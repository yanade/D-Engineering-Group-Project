# tests/test_load_service.py
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence

import pandas as pd
import pytest
from botocore.exceptions import ClientError

from loading.load_service import LoadService


# -----------------------------
# Fakes
# -----------------------------

class _FakeBody:
    def __init__(self, data: bytes):
        self._data = data

    def read(self) -> bytes:
        return self._data


@dataclass
class FakeS3Api:
  
    objects: Dict[str, bytes] = field(default_factory=dict)

    def get_object(self, Bucket: str, Key: str) -> Dict[str, Any]:
        if Key not in self.objects:
            raise ClientError(
                {"Error": {"Code": "NoSuchKey", "Message": "Not Found"}},
                "GetObject",
            )
        return {"Body": _FakeBody(self.objects[Key])}

    def put_object(
        self,
        Bucket: str,
        Key: str,
        Body: bytes,
        ContentType: str = "application/json",
    ) -> Dict[str, Any]:
        self.objects[Key] = Body
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}


@dataclass
class FakeS3LoadingClient:
    """
    Fake S3 client wrapper expected by LoadService:
    - has .s3 (low-level API) with get_object/put_object
    - can list parquet keys and return DataFrames
    """
    s3: Any = field(default_factory=FakeS3Api)
    parquet: Dict[str, pd.DataFrame] = field(default_factory=dict)

    def list_parquet_keys(self, table: str) -> List[str]:
        # match real behaviour: keys look like "{table}/something.parquet"
        return sorted([k for k in self.parquet if k.startswith(f"{table}/")])

    def read_parquet_to_df(self, key: str) -> pd.DataFrame:
        return self.parquet[key].copy()


@dataclass
class FakeDB:
    executed_sql: List[str] = field(default_factory=list)
    executemany_calls: List[Dict[str, Any]] = field(default_factory=list)

    def execute(self, sql: str) -> None:
        self.executed_sql.append(sql)

    def executemany(
        self,
        sql: str,
        params: List[Sequence[Any]],
        chunk_size: int = 1000,
    ) -> None:
        self.executemany_calls.append(
            {"sql": sql, "params": params, "chunk_size": chunk_size}
        )

    def fetchall(self, sql, params=None):
        table = params[0] if params else None

        # A) SchemaCoercer запросив (column_name, data_type, is_nullable)
        if "data_type" in sql and "is_nullable" in sql:
            if table == "dim_staff":
                return [
                    ("staff_id", "integer", "NO"),
                    ("name", "text", "NO"),
                ]
            if table == "fact_sales_order":
                return [
                    ("order_id", "integer", "NO"),
                    ("last_updated_date", "text", "NO"),
                    ("last_updated_time", "text", "NO"),
                ]
            return []

        # B) LoadService запросив тільки column_name
        if table == "dim_staff":
            return [("staff_id",), ("name",)]
        if table == "fact_sales_order":
            return [("order_id",), ("last_updated_date",), ("last_updated_time",)]

        return []




# Tests

def test_dim_snapshot_truncates_and_inserts(monkeypatch):
    table = "dim_staff"

    fake_db = FakeDB()
    fake_s3 = FakeS3LoadingClient()
    fake_s3.parquet[f"{table}/part-000.parquet"] = pd.DataFrame(
        [{"staff_id": 1, "name": "A"}, {"staff_id": 2, "name": "B"}]
    )

    svc = LoadService(processed_bucket="fake-processed", db=fake_db)
    svc.s3_client = fake_s3

    # Typed DDL must exist for create_table_if_not_exists()
    monkeypatch.setattr(
        "loading.load_service.CREATE_TABLE_SQL",
        {table: f'CREATE TABLE IF NOT EXISTS "{table}" (staff_id INT, name TEXT);'},
        raising=True,
    )

    res = svc.load_one_table(table)

    assert res["status"] == "loaded"
    assert res["mode"] == "snapshot_upsert"
    assert res["rows"] == 2

    assert any("CREATE TABLE IF NOT EXISTS" in s for s in fake_db.executed_sql)

    assert len(fake_db.executemany_calls) == 1
    assert len(fake_db.executemany_calls[0]["params"]) == 2


def test_fact_delta_filters_by_watermark_and_writes_checkpoint(monkeypatch):
    table = "fact_sales_order"

    fake_db = FakeDB()
    fake_s3 = FakeS3LoadingClient()

    # Two parquet versions; service picks the latest by sorted key order
    old_key = f"{table}/part-000.parquet"
    latest_key = f"{table}/part-001.parquet"

    # Latest parquet has 3 rows; only 2 should be NEW after watermark
    fake_s3.parquet[latest_key] = pd.DataFrame(
        [
            # old (<= last_loaded_ts) -> should be filtered out
            {"order_id": 1, "last_updated_date": "2026-01-01", "last_updated_time": "10:00:00"},
            # new
            {"order_id": 2, "last_updated_date": "2026-01-01", "last_updated_time": "10:00:01"},
            # new (max)
            {"order_id": 3, "last_updated_date": "2026-01-01", "last_updated_time": "10:05:00"},
        ]
    )

    # Also include an older parquet key just to show "latest selection" works
    fake_s3.parquet[old_key] = pd.DataFrame(
        [{"order_id": 999, "last_updated_date": "2025-12-31", "last_updated_time": "23:59:59"}]
    )

    svc = LoadService(processed_bucket="fake-processed", db=fake_db)
    svc.s3_client = fake_s3

    # Typed DDL must exist
    monkeypatch.setattr(
        "loading.load_service.CREATE_TABLE_SQL",
        {
            table: (
                f'CREATE TABLE IF NOT EXISTS "{table}" ('
                "order_id INT, last_updated_date TEXT, last_updated_time TEXT);"
            )
        },
        raising=True,
    )

    # Seed checkpoint in fake S3 so watermark is applied:
    # last_loaded_ts == 10:00:00Z, so rows > 10:00:00 are new (2 rows)
    ckpt_key = f"{svc.checkpoints_prefix}/{table}.json"
    fake_s3.s3.objects[ckpt_key] = json.dumps(
        {
            "last_loaded_key": old_key,
            "last_loaded_ts": "2026-01-01T10:00:00Z",
            "updated_at": "2026-01-01T10:00:00Z",
        }
    ).encode("utf-8")

    res = svc.load_one_table(table)

    assert res["status"] == "loaded"
    assert res["mode"] == "delta"
    assert res["latest_key"] == latest_key
    assert res["rows"] == 2
    assert res["watermark"] == "last_updated_date+time"

    # Facts should NOT truncate
    assert not any("TRUNCATE TABLE" in s for s in fake_db.executed_sql)

    # Insert should be 2 rows
    assert len(fake_db.executemany_calls) == 1
    inserted_params = fake_db.executemany_calls[0]["params"]
    assert len(inserted_params) == 2

    # Checkpoint should be updated in fake S3
    assert ckpt_key in fake_s3.s3.objects
    updated_ckpt = json.loads(fake_s3.s3.objects[ckpt_key].decode("utf-8"))

    assert updated_ckpt["last_loaded_key"] == latest_key
    # max watermark among inserted rows is 10:05:00Z
    assert updated_ckpt["last_loaded_ts"] == "2026-01-01T10:05:00Z"
    assert "updated_at" in updated_ckpt


def test_fact_skips_if_latest_key_already_loaded(monkeypatch):
    table = "fact_payment"

    fake_db = FakeDB()
    fake_s3 = FakeS3LoadingClient()

    latest_key = f"{table}/part-010.parquet"
    fake_s3.parquet[latest_key] = pd.DataFrame(
        [{"payment_id": 1, "updated_at": "2026-01-02T12:00:00Z"}]
    )

    svc = LoadService(processed_bucket="fake-processed", db=fake_db)
    svc.s3_client = fake_s3

    monkeypatch.setattr(
        "loading.load_service.CREATE_TABLE_SQL",
        {table: f'CREATE TABLE IF NOT EXISTS "{table}" (payment_id INT, updated_at TEXT);'},
        raising=True,
    )

    # Seed checkpoint with the same latest key -> should skip
    ckpt_key = f"{svc.checkpoints_prefix}/{table}.json"
    fake_s3.s3.objects[ckpt_key] = json.dumps(
        {"last_loaded_key": latest_key, "last_loaded_ts": "2026-01-02T12:00:00Z", "updated_at": "2026-01-02T12:00:00Z"}
    ).encode("utf-8")

    res = svc.load_one_table(table)

    assert res["status"] == "skipped"
    assert res["reason"] == "already_loaded"
    assert res["latest_key"] == latest_key

    # No DB writes
    assert fake_db.executed_sql == []
    assert fake_db.executemany_calls == []

