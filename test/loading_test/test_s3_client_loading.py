from loading.s3_client import S3LoaderClient

import pytest
import pandas as pd 
from datetime import datetime, timezone
from io import BytesIO


def test_s3_client_initialises_correctly():
    client = S3LoaderClient(bucket="test-bucket")

    assert client.bucket == "test-bucket"
    assert client.s3 is not None

# ----------------------------
# Fake S3 client
# ----------------------------
class FakeBotoS3:
    def __init__(self):
        self.objects = {}  
        self.listing = []   

    def list_objects_v2(self, Bucket, Prefix, MaxKeys=None):
        contents = [
            obj for obj in self.listing
            if obj["Key"].startswith(Prefix)
        ]
        return {"Contents": contents} if contents else {}

    def get_object(self, Bucket, Key):
        return {
            "Body": BytesIO(self.objects[(Bucket, Key)])
        }


# ----------------------------
# Tests
# ----------------------------
def test_read_latest_parquet_reads_most_recent(monkeypatch):
    fake_s3 = FakeBotoS3()

    # Seed parquet objects
    fake_s3.listing = [
        {
            "Key": "fact_sales_order/old.parquet",
            "LastModified": datetime(2024, 1, 1, tzinfo=timezone.utc),
        },
        {
            "Key": "fact_sales_order/new.parquet",
            "LastModified": datetime(2024, 2, 1, tzinfo=timezone.utc),
        },
    ]

    fake_s3.objects[("processed", "fact_sales_order/new.parquet")] = b"PARQUET_BYTES"

    # Patch boto3.client WHERE IT'S USED
    import loading.s3_client as s3_mod
    monkeypatch.setattr(s3_mod.boto3, "client", lambda *args, **kwargs: fake_s3)

    # Patch pandas.read_parquet so pyarrow is NOT required
    expected_df = pd.DataFrame({"id": [1]})
    monkeypatch.setattr(pd, "read_parquet", lambda buffer: expected_df)

    client = S3LoaderClient(bucket="processed")
    df = client.read_latest_parquet("fact_sales_order")

    assert isinstance(df, pd.DataFrame)
    assert df.equals(expected_df)


def test_read_latest_parquet_raises_if_no_objects(monkeypatch):
    fake_s3 = FakeBotoS3()

    import loading.s3_client as s3_mod
    monkeypatch.setattr(s3_mod.boto3, "client", lambda *args, **kwargs: fake_s3)

    client = S3LoaderClient(bucket="processed")

    with pytest.raises(FileNotFoundError, match="No objects found"):
        client.read_latest_parquet("dim_currency")


def test_read_latest_parquet_raises_if_no_parquet_files(monkeypatch):
    fake_s3 = FakeBotoS3()

    fake_s3.listing = [
        {
            "Key": "dim_currency/readme.txt",
            "LastModified": datetime.now(timezone.utc),
        }
    ]

    import loading.s3_client as s3_mod
    monkeypatch.setattr(s3_mod.boto3, "client", lambda *args, **kwargs: fake_s3)

    client = S3LoaderClient(bucket="processed")

    with pytest.raises(FileNotFoundError, match="No parquet files"):
        client.read_latest_parquet("dim_currency")


def test_read_parquet_calls_pandas(monkeypatch):
    fake_s3 = FakeBotoS3()
    fake_s3.objects[("processed", "dim_staff/file.parquet")] = b"PARQUET_BYTES"

    import loading.s3_client as s3_mod
    monkeypatch.setattr(s3_mod.boto3, "client", lambda *args, **kwargs: fake_s3)

    expected_df = pd.DataFrame({"name": ["Alice"]})
    read_parquet_spy = monkeypatch.setattr(
        pd,
        "read_parquet",
        lambda buffer: expected_df
    )

    client = S3LoaderClient(bucket="processed")
    df = client.read_parquet("dim_staff/file.parquet")

    assert df.equals(expected_df)