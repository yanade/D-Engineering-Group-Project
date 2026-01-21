from __future__ import annotations

import io
import json
from dataclasses import dataclass, field
from typing import Any, Dict, List

import pandas as pd

from loading.load_service import LoadService


def test_fact_skips_when_checkpoint_last_loaded_key_equals_latest(monkeypatch):
    # ---- FAKES ----
    @dataclass
    class FakeDB:
        executed_sql: List[str] = field(default_factory=list)
        executemany_calls: List[Dict[str, Any]] = field(default_factory=list)

        def execute(self, sql: str) -> None:
            self.executed_sql.append(sql)

        def executemany(self, sql: str, params: List[Any], chunk_size: int = 1000) -> None:
            self.executemany_calls.append({"sql": sql, "params": params, "chunk_size": chunk_size})

    @dataclass
    class FakeS3Api:
        objects: Dict[str, bytes] = field(default_factory=dict)

        def get_object(self, Bucket: str, Key: str):
            if Key not in self.objects:
                from botocore.exceptions import ClientError

                raise ClientError(
                    {"Error": {"Code": "NoSuchKey", "Message": "Not Found"}},
                    "GetObject",
                )
            return {"Body": io.BytesIO(self.objects[Key])}

        def put_object(self, Bucket: str, Key: str, Body: bytes, ContentType: str):
            self.objects[Key] = Body
            return {"ResponseMetadata": {"HTTPStatusCode": 200}}

    @dataclass
    class FakeS3LoadingClient:
        s3: Any = field(default_factory=FakeS3Api)
        parquet: Dict[str, pd.DataFrame] = field(default_factory=dict)

        def list_parquet_keys(self, table: str) -> List[str]:
            return sorted([k for k in self.parquet if k.startswith(f"{table}/")])

        def read_parquet_to_df(self, key: str) -> pd.DataFrame:
            return self.parquet[key].copy()

    # ---- Arrange ----
    table = "fact_sales_order"
    fake_db = FakeDB()
    fake_s3 = FakeS3LoadingClient()

    fake_s3.parquet[f"{table}/fileA.parquet"] = pd.DataFrame(
        [{"sales_order_id": 1, "last_updated": "2026-01-06T10:00:00Z"}]
    )
    fake_s3.parquet[f"{table}/fileB.parquet"] = pd.DataFrame(
        [{"sales_order_id": 2, "last_updated": "2026-01-06T10:05:00Z"}]
    )

    ckpt_key = f"_load_checkpoints/{table}.json"
    fake_s3.s3.objects[ckpt_key] = json.dumps(
        {"last_loaded_key": f"{table}/fileB.parquet", "last_loaded_ts": "2026-01-06T10:05:00Z"}
    ).encode("utf-8")

    svc = LoadService(processed_bucket="fake-processed", db=fake_db)
    svc.s3_client = fake_s3

    monkeypatch.setattr(
        "loading.load_service.CREATE_TABLE_SQL",
        {table: f'CREATE TABLE IF NOT EXISTS "{table}" (sales_order_id INT, last_updated TIMESTAMPTZ);'},
        raising=True,
    )

    # ---- Act ----
    res = svc.load_one_table(table)

    # ---- Assert ----
    assert res["status"] == "skipped"
    assert res["reason"] == "already_loaded"
    assert res["latest_key"] == f"{table}/fileB.parquet"

    assert len(fake_db.executemany_calls) == 0
