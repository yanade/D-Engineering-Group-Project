import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple
from botocore.exceptions import ClientError


from loading.sql import CREATE_TABLE_SQL


import pandas as pd

from loading.db_client import WarehouseDBClient
from loading.s3_client import S3LoadingClient
from loading.schema_coercion import SchemaCoercer

logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))


class LoadService:

    # Loading Zone:
    # - Discover tables from processed S3 (dim_* and fact_*)
    # - dim_*  => snapshot load (TRUNCATE + INSERT)
    # - fact_* => append only NEW rows (watermark filter) + checkpoint in S3

    # Checkpoints (in processed bucket):

    def __init__(
        self,
        processed_bucket: str,
        db: WarehouseDBClient,
        checkpoints_prefix: str = "_load_checkpoints",
    ):
        self.processed_bucket = processed_bucket
        self.s3_client = S3LoadingClient(bucket=processed_bucket)
        self.db = db
        self.checkpoints_prefix = checkpoints_prefix.rstrip("/")
        self.coercer = SchemaCoercer(db=self.db)
        logger.info(
            "Initialising LoadService with bucket=%s",
            processed_bucket)

    # Discovery + ordering

    def _discover_tables_from_s3(self) -> List[str]:
        """
        Lists top-level prefixes in processed bucket (folders).
        Only keeps dim_* and fact_* prefixes.
        """
        paginator = self.s3_client.s3.get_paginator("list_objects_v2")
        tables: List[str] = []

        for page in paginator.paginate(
                Bucket=self.processed_bucket,
                Delimiter="/"):
            for prefix in page.get("CommonPrefixes", []):
                name = prefix.get("Prefix", "").rstrip("/")
                if not name:
                    continue
                if name.startswith("_"):
                    continue
                if name.startswith(("dim_", "fact_")):
                    tables.append(name)

        tables = sorted(set(tables))
        logger.info("Discovered tables in S3: %s", tables)
        return tables

    def _rank(self, table: str) -> Tuple[int, str]:
        if table.startswith("dim_"):
            return (0, table)
        if table.startswith("fact_"):
            return (1, table)
        return (2, table)

    def _order_tables(self, tables: List[str]) -> List[str]:
        return sorted(tables, key=self._rank)

    def _should_truncate(self, table: str) -> bool:
        # dims snapshot; facts append
        return table.startswith("dim_")

    def _is_fact(self, table: str) -> bool:
        return table.startswith("fact_")

    # Public API

    def load_all_tables(self) -> Dict[str, Any]:
        tables = self._order_tables(self._discover_tables_from_s3())
        results: List[Dict[str, Any]] = []

        for table in tables:
            results.append(self.load_one_table(table))

        return {"processed_bucket": self.processed_bucket, "tables": results}

    def load_one_table(self, table: str) -> Dict[str, Any]:
        logger.info("Loading table=%s", table)

        # 1) Find latest parquet key for this table
        parquet_keys = self.s3_client.list_parquet_keys(table)
        if not parquet_keys:
            logger.warning("Skip table=%s (no parquet).", table)
            return {
                "table": table,
                "status": "skipped",
                "reason": "no_parquet"}

        latest_key = parquet_keys[-1]

        # 2) Check checkpoint (for facts: skip if same parquet already loaded)
        # 2) Checkpoint (facts only)
        ckpt: Dict[str, Any] = {}
        if self._is_fact(table):
            ckpt = self._read_checkpoint(table)

        if self._is_fact(table) and ckpt.get("last_loaded_key") == latest_key:
            logger.info(
                "Skip fact table=%s (already loaded key=%s).",
                table,
                latest_key)
            return {
                "table": table,
                "status": "skipped",
                "reason": "already_loaded",
                "latest_key": latest_key}

        # 3) Read latest parquet
        df = self.s3_client.read_parquet_to_df(latest_key)
        if df is None or df.empty:
            logger.warning(
                "Skip table=%s (empty parquet). key=%s",
                table,
                latest_key)
            # checkpoint key so we don't reprocess the same empty file
            # repeatedly
            if self._is_fact(table):
                self._write_checkpoint(
                    table,
                    last_loaded_key=latest_key,
                    last_loaded_ts=ckpt.get("last_loaded_ts"))
            return {
                "table": table,
                "status": "skipped",
                "reason": "no_data",
                "latest_key": latest_key}

        # Ensure NULLs handled (NaN/NaT -> None)
        df = df.where(pd.notnull(df), None)

        # 4) Create table if needed (MVP only)
        self.create_table_if_not_exists(table, df)
        df = self.coercer.coerce_df(table=table, df=df, text_default="Unknown")

        # 5) dim snapshot
        if self._should_truncate(table):
            self.truncate_table(table)
            inserted = self._insert_df(table, df)
            # dims don't need watermark; keep checkpoint optional (not
            # required)
            logger.info(
                "Loaded dim snapshot table=%s rows=%s",
                table,
                inserted)
            return {
                "table": table,
                "status": "loaded",
                "mode": "snapshot",
                "rows": inserted,
                "latest_key": latest_key}

        # 6) fact delta: watermark filter (append only NEW rows)
        df_to_insert = df
        wm_name, wm_series = self._detect_watermark(df)
        last_ts = ckpt.get("last_loaded_ts")

        if wm_name and wm_series is not None and last_ts:
            last_dt = self._parse_ts(last_ts)
            before = len(df_to_insert)
            df_to_insert = df_to_insert.loc[wm_series > last_dt].copy()
            logger.info(
                "Filtered NEW rows for fact table=%s watermark=%s > %s: %s -> %s",
                table,
                wm_name,
                last_ts,
                before,
                len(df_to_insert))

        inserted = self._insert_df(table, df_to_insert)

        # Update checkpoint:
        # - Always update last_loaded_key to avoid reprocessing same file forever
        # - Update last_loaded_ts ONLY if we actually inserted something
        if inserted > 0:
            new_last_ts = self._max_watermark_iso(df_to_insert)
        else:
            new_last_ts = ckpt.get("last_loaded_ts")

        self._write_checkpoint(
            table,
            last_loaded_key=latest_key,
            last_loaded_ts=new_last_ts)

        mode = "delta"
        if wm_name is None:
            mode = "append_no_watermark"

        return {
            "table": table,
            "status": "loaded",
            "mode": mode,
            "rows": inserted,
            "latest_key": latest_key,
            "watermark": wm_name,
        }

    # DB helpers (MVP)

    def create_table_if_not_exists(self, table: str, df: pd.DataFrame) -> None:

        ddl = CREATE_TABLE_SQL.get(table)
        if not ddl:
            raise KeyError(
                f"No typed DDL found for table={table}. "
                "Add it to loading/sql.py CREATE_TABLE_SQL.")

        logger.info("Ensuring table exists (typed DDL): %s", table)
        self.db.execute(ddl)

    def truncate_table(self, table: str) -> None:
        truncate_sql = f'TRUNCATE TABLE "{table}";'
        logger.info("Truncating table: %s", table)
        self.db.execute(truncate_sql)

    def _insert_df(self, table: str, df: pd.DataFrame) -> int:
        """
        Bulk insert DataFrame rows into table using ONLY columns that exist in DB.
        Returns inserted row count.
        """
        if df is None or df.empty:
            return 0

        # 1) Get DB column order (source of truth)
        db_cols = self._get_db_columns(table)
        if not db_cols:
            raise ValueError(
                f"Table {table} has no columns in information_schema (unexpected)")

        # 2) Keep only intersection, preserving DB order (important for BI
        # consistency)
        insert_cols = [c for c in db_cols if c in df.columns]

        if not insert_cols:
            raise ValueError(
                f"No matching columns between df and DB table. table={table} df_cols={
                    list(
                        df.columns)}")

        dropped = [c for c in df.columns if c not in insert_cols]
        if dropped:
            logger.warning(
                "Insert filtering: table=%s dropping df columns not in DB schema: %s",
                table,
                dropped)

        # 3) Slice df to insert columns (correct order)
        df2 = df[insert_cols].copy()

        # 4) Build INSERT
        col_list = ", ".join([f'"{c}"' for c in insert_cols])
        placeholders = ", ".join(["%s"] * len(insert_cols))
        sql = f'INSERT INTO "{table}" ({col_list}) VALUES ({placeholders});'

        # 5) Build params (convert pandas missing to None just in case)
        df2 = df2.where(pd.notnull(df2), None)
        params: List[Sequence[Any]] = [
            tuple(row) for row in df2.itertuples(index=False, name=None)]

        self.db.executemany(sql, params, chunk_size=1000)

        logger.info(
            "Inserted %s rows into table=%s cols=%s",
            len(params),
            table,
            insert_cols,
        )
        return len(params)

    def _get_db_columns(self, table: str) -> List[str]:
        sql = """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position;
        """
        rows = self.db.fetchall(sql, (table,))
        return [r[0] for r in rows]

    # Watermark detection

    def _detect_watermark(self,
                          df: pd.DataFrame) -> Tuple[Optional[str],
                                                     Optional[pd.Series]]:
        """
        Detect a watermark datetime Series (UTC) for filtering NEW fact rows.
        Supports your TransformService outputs (best case: last_updated_date + last_updated_time).
        """
        cols = set(df.columns)

        # Best: last_updated_date + last_updated_time
        if {"last_updated_date", "last_updated_time"}.issubset(cols):
            dt_str = df["last_updated_date"].astype(
                str) + " " + df["last_updated_time"].astype(str)
            wm = pd.to_datetime(dt_str, errors="coerce", utc=True)
            if wm.notna().any():
                return "last_updated_date+time", wm

        # Next best: single timestamp column
        for c in ["last_updated", "updated_at", "created_at", "payment_date"]:
            if c in cols:
                wm = pd.to_datetime(df[c], errors="coerce", utc=True)
                if wm.notna().any():
                    return c, wm

        return None, None

    def _max_watermark_iso(self, df: pd.DataFrame) -> Optional[str]:
        name, wm = self._detect_watermark(df)
        if name is None or wm is None:
            return None

        max_dt = wm.max()
        if pd.isna(max_dt):
            return None

        if hasattr(max_dt, "to_pydatetime"):
            max_dt = max_dt.to_pydatetime()

        max_dt = max_dt.astimezone(timezone.utc).replace(microsecond=0)
        return max_dt.isoformat().replace("+00:00", "Z")

    def _parse_ts(self, ts: str) -> datetime:
        """
        Parse ISO timestamp saved in checkpoint.
        Accepts "...Z" or "...+00:00".
        """
        if ts.endswith("Z"):
            ts = ts.replace("Z", "+00:00")
        return datetime.fromisoformat(ts).astimezone(timezone.utc)

    # Checkpoints in S3 (facts)

    def _checkpoint_key(self, table: str) -> str:
        return f"{self.checkpoints_prefix}/{table}.json"

    def _read_checkpoint(self, table: str) -> Dict[str, Any]:
        """
        Read checkpoint JSON. Returns {} if not found.
        Raises on other errors (so you see IAM/JSON issues).
        """
        key = self._checkpoint_key(table)
        try:
            obj = self.s3_client.s3.get_object(
                Bucket=self.processed_bucket, Key=key)
            data = obj["Body"].read().decode("utf-8")
            payload = json.loads(data)
            return payload if isinstance(payload, dict) else {}
        except ClientError as e:
            code = e.response.get("Error", {}).get("Code")
            if code in ("NoSuchKey", "404"):
                return {}
            logger.exception(
                "Failed to read checkpoint table=%s key=%s", table, key)
            raise

    def _write_checkpoint(
            self,
            table: str,
            last_loaded_key: str,
            last_loaded_ts: Optional[str]) -> None:
        key = self._checkpoint_key(table)
        payload = {
            "last_loaded_key": last_loaded_key,
            "last_loaded_ts": last_loaded_ts,
            "updated_at": datetime.now(
                timezone.utc).replace(
                microsecond=0).isoformat().replace(
                "+00:00",
                "Z"),
        }
        self.s3_client.s3.put_object(
            Bucket=self.processed_bucket,
            Key=key,
            Body=json.dumps(payload).encode("utf-8"),
            ContentType="application/json",
        )
        logger.info("Wrote checkpoint table=%s key=%s ts=%s",
                    table, last_loaded_key, last_loaded_ts)
