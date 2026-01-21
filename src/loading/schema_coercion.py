# src/loading/schema_coercion.py

import logging
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class SchemaCoercer:
    """
    Schema-driven coercion for Pandas DataFrame before inserting into Postgres.

    Approach:
    - Read table schema from information_schema.columns
    - For each df column that exists in DB schema, coerce values to match DB type
    - Convert pandas missing values (NaN/NaT) to Python None for pg8000/DBAPI
    - BI-friendly: fill NOT NULL text columns with a default value (e.g. "Unknown")

    Supported Postgres data_type values (information_schema.columns.data_type):
    - text, character varying, character
    - integer, bigint, smallint
    - numeric, decimal, real, double precision
    - boolean
    - date
    - time without time zone (and "time")
    - timestamp without time zone, timestamp with time zone (and "timestamp")
    - uuid  (kept as string)
    """

    def __init__(self, db: Any):
      
        self.db = db

    def coerce_df(self, table: str, df: pd.DataFrame, text_default: str = "Unknown") -> pd.DataFrame:
        """
        Main entry point. Returns a coerced copy (or same df mutated).
        """
        # Step 1: quick exit
        if df is None or df.empty:
            logger.info("Coercion skipped: table=%s (empty dataframe)", table)
            return df

        # Step 2: replace obvious missing values
        # (we still do per-type conversion after this)
        df = df.where(pd.notnull(df), None)

        # Step 3: load schema
        schema = self._load_schema(table)
        if not schema:
            logger.warning("Coercion: table=%s (no schema rows found)", table)
            return df

        logger.info(
            "Coercion: table=%s schema_cols=%s df_cols=%s",
            table,
            len(schema),
            len(df.columns),
        )

        # Step 4: coerce only columns that exist in BOTH df and schema
        for col in df.columns:
            if col not in schema:
                logger.debug("Coercion: table=%s df_col=%s not in DB schema -> skip", table, col)
                continue

            data_type, is_nullable = schema[col]

            # TEXT-like
            if data_type in ("text", "character varying", "character"):
                df[col] = self._coerce_text_col(df[col], is_nullable, text_default)
                continue

            # INTEGER-like
            if data_type in ("integer", "bigint", "smallint"):
                df[col] = self._coerce_int_col(df[col], table, col)
                continue

            # NUMERIC / FLOAT-like
            if data_type in ("numeric", "decimal", "real", "double precision"):
                df[col] = self._coerce_numeric_col(df[col], table, col, data_type)
                continue

            # BOOLEAN
            if data_type == "boolean":
                df[col] = self._coerce_bool_col(df[col], table, col)
                continue

            # DATE
            if data_type == "date":
                df[col] = self._coerce_date_col(df[col], table, col)
                continue

            # TIME
            if data_type in ("time without time zone", "time"):
                df[col] = self._coerce_time_col(df[col], table, col)
                continue

            # TIMESTAMP
            if data_type in ("timestamp without time zone", "timestamp with time zone", "timestamp"):
                df[col] = self._coerce_timestamp_col(df[col], table, col, data_type)
                continue

            # UUID
            if data_type == "uuid":
                df[col] = self._coerce_uuid_col(df[col])
                continue

            # Unknown/custom types: only make sure missing -> None
            logger.debug("Coercion: table=%s col=%s type=%s (unhandled) -> leave as-is", table, col, data_type)
            df[col] = df[col].where(pd.notnull(df[col]), None)

        return df


    # Schema loading


    def _load_schema(self, table: str) -> Dict[str, Tuple[str, str]]:
        """
        Returns mapping: column_name -> (data_type, is_nullable)
        """
        schema_sql = """
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s;
        """
        rows = self.db.fetchall(schema_sql, (table,))
        return {r[0]: (r[1], r[2]) for r in rows}

 
    # Helpers (type coercion)
 

    def _coerce_text_col(self, s: pd.Series, is_nullable: str, text_default: str) -> pd.Series:
        """
        Convert values to strings, keep None as None.
        If NOT NULL, fill missing with text_default (BI-friendly).
        """
        def to_text(v: Any) -> Any:
            if v is None:
                return None
            return str(v)

        out = s.map(to_text)

        if is_nullable == "NO":
            out = out.fillna(text_default)

        return out

    def _coerce_int_col(self, s: pd.Series, table: str, col: str) -> pd.Series:
        """
        Coerce to integer:
        - parse numeric
        - invalid -> NULL
        - non-integers -> NULL
        - return Python ints or None
        """
        num = pd.to_numeric(s, errors="coerce")

        # invalid values: parsing failed but original not null
        invalid_mask = num.isna() & s.notna()
        invalid_count = int(invalid_mask.sum())
        if invalid_count > 0:
            logger.warning("Coercion int: table=%s col=%s invalid_values=%s -> set to NULL", table, col, invalid_count)

        # non-integers: numeric but not whole number
        non_int_mask = num.notna() & (num % 1 != 0)
        non_int_count = int(non_int_mask.sum())
        if non_int_count > 0:
            logger.warning("Coercion int: table=%s col=%s non_integer_values=%s -> set to NULL", table, col, non_int_count)
            num[non_int_mask] = pd.NA

        # pandas nullable int, then convert <NA> to None
        out = num.astype("Int64").astype(object)
        out = out.where(pd.notnull(out), None)
        return out

    def _coerce_numeric_col(self, s: pd.Series, table: str, col: str, data_type: str) -> pd.Series:
        """
        Coerce to Decimal for numeric stability.
        Invalid -> NULL.
        """
        def to_decimal(v: Any) -> Any:
            if v is None:
                return None
            if isinstance(v, float) and pd.isna(v):
                return None
            try:
                return Decimal(str(v))
            except (InvalidOperation, ValueError, TypeError):
                return None

        out = s.map(to_decimal)

        # count invalid-to-null (approx)
        original_non_null = int(s.notna().sum())
        new_non_null = int(pd.Series(out).notna().sum())
        invalid_to_null = max(0, original_non_null - new_non_null)
        if invalid_to_null > 0:
            logger.warning(
                "Coercion numeric: table=%s col=%s type=%s invalid_to_null=%s",
                table,
                col,
                data_type,
                invalid_to_null,
            )

        return out

    def _coerce_bool_col(self, s: pd.Series, table: str, col: str) -> pd.Series:
        """
        Coerce to bool:
        Accepts: true/false, t/f, 1/0, yes/no, y/n
        Invalid -> NULL
        """
        true_set = {"true", "t", "1", "yes", "y"}
        false_set = {"false", "f", "0", "no", "n"}

        def to_bool(v: Any) -> Any:
            if v is None:
                return None
            if isinstance(v, bool):
                return v
            if isinstance(v, (int,)):
                if v == 1:
                    return True
                if v == 0:
                    return False
                return None
            if isinstance(v, float) and not pd.isna(v):
                if v == 1.0:
                    return True
                if v == 0.0:
                    return False
                return None
            if isinstance(v, str):
                vv = v.strip().lower()
                if vv in true_set:
                    return True
                if vv in false_set:
                    return False
                return None
            return None

        out = s.map(to_bool)

        # invalid-to-null (approx)
        original_non_null = int(s.notna().sum())
        new_non_null = int(pd.Series(out).notna().sum())
        invalid_to_null = max(0, original_non_null - new_non_null)
        if invalid_to_null > 0:
            logger.warning("Coercion bool: table=%s col=%s invalid_to_null=%s", table, col, invalid_to_null)

        return out

    def _coerce_date_col(self, s: pd.Series, table: str, col: str) -> pd.Series:
        """
        Coerce to python date.
        Invalid -> NULL.
        """
        dt = pd.to_datetime(s, errors="coerce", utc=False)
        out = dt.dt.date.astype(object)
        out = out.where(pd.notnull(out), None)

        invalid_mask = dt.isna() & s.notna()
        invalid_count = int(invalid_mask.sum())
        if invalid_count > 0:
            logger.warning("Coercion date: table=%s col=%s invalid_to_null=%s", table, col, invalid_count)

        return out

    def _coerce_time_col(self, s: pd.Series, table: str, col: str) -> pd.Series:
        """
        Coerce to python time.
        - If series already contains datetime.time objects -> keep as is (only normalize None).
        - Else try to parse with pd.to_datetime.
        Invalid -> NULL.
        """
        import datetime as dt

        non_null = s.dropna()
        if non_null.empty:
            return s.where(pd.notnull(s), None)

        sample = non_null.iloc[0]

       
        if isinstance(sample, dt.time):
            out = s.astype(object)
            out = out.where(pd.notnull(out), None)
            return out

        if isinstance(sample, pd.Timestamp) or str(s.dtype).startswith("datetime64"):
            dt_vals = pd.to_datetime(s, errors="coerce")
            out = dt_vals.dt.time.astype(object)
            out = out.where(pd.notnull(out), None)

            invalid_mask = dt_vals.isna() & s.notna()
            invalid_count = int(invalid_mask.sum())
            if invalid_count > 0:
                logger.warning(
                    "Coercion time: table=%s col=%s invalid_to_null=%s",
                    table,
                    col,
                    invalid_count,
                )
            return out

      
        dt_vals = pd.to_datetime(s, errors="coerce")
        out = dt_vals.dt.time.astype(object)
        out = out.where(pd.notnull(out), None)

        invalid_mask = dt_vals.isna() & s.notna()
        invalid_count = int(invalid_mask.sum())
        if invalid_count > 0:
            logger.warning(
                "Coercion time: table=%s col=%s invalid_to_null=%s",
                table,
                col,
                invalid_count,
            )

        return out


    def _coerce_timestamp_col(self, s: pd.Series, table: str, col: str, data_type: str) -> pd.Series:
        """
        Coerce to datetime.
        - timestamp with time zone -> UTC-aware
        - timestamp without time zone -> naive datetime
        Invalid -> NULL
        """
        if data_type == "timestamp with time zone":
            dt = pd.to_datetime(s, errors="coerce", utc=True)
            out = dt.astype(object)
        else:
            dt = pd.to_datetime(s, errors="coerce", utc=False)
            out = dt.astype(object)

        out = out.where(pd.notnull(out), None)

        invalid_mask = dt.isna() & s.notna()
        invalid_count = int(invalid_mask.sum())
        if invalid_count > 0:
            logger.warning(
                "Coercion timestamp: table=%s col=%s type=%s invalid_to_null=%s",
                table,
                col,
                data_type,
                invalid_count,
            )

        return out

    def _coerce_uuid_col(self, s: pd.Series) -> pd.Series:
        """
        Keep UUID as string; invalid -> NULL.
        """
        def to_uuid_str(v: Any) -> Any:
            if v is None:
                return None
            return str(v)

        out = s.map(to_uuid_str)
        return out
