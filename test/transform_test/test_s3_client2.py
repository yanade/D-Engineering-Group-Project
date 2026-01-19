import json
import pandas as pd
from datetime import datetime, timezone
import io
from io import BytesIO
import json
import pandas as pd
import pytest
from transformation.s3_client import S3TransformationClient


def test_read_raw_json_list_format(mocker):
    """Test reading a raw ingestion file where the content is a list of dicts."""
    s3 = mocker.Mock()
    mocker.patch("boto3.client", return_value=s3)

    raw_data = [{"id": 1, "name": "Alice"}]
    s3.get_object.return_value = {"Body": BytesIO(json.dumps(raw_data).encode("utf-8"))}

    client = S3TransformationClient("landing-bucket")
    rows = client.read_json("staff/raw.json")

    assert rows == raw_data
    assert "staff" == "staff/raw.json".split("/")[0]


class FakeBotoS3:
    """Minimal fake boto3 S3 client."""
    def __init__(self):
        self.objects = {}  # {(Bucket, Key): bytes}

    def get_object(self, Bucket, Key):
        body = self.objects[(Bucket, Key)]
        return {"Body": io.BytesIO(body)}

    def put_object(self, Bucket, Key, Body):
        if isinstance(Body, str):
            Body = Body.encode("utf-8")
        self.objects[(Bucket, Key)] = Body
        return {"ResponseMetadata": {"HTTPStatusCode": 200}}




def test_write_parquet_puts_object(monkeypatch):
    fake_s3 = FakeBotoS3()

    import transformation.s3_client as s3_mod
    monkeypatch.setattr(s3_mod.boto3, "client", lambda service: fake_s3)

    client = S3TransformationClient(bucket="processed")
    df = pd.DataFrame({"id": [1], "name": ["Alice"]})

    key = client.write_parquet("dim_test", df)

    # Verify it wrote something to S3 under returned key
    assert ("processed", key) in fake_s3.objects
    assert key.startswith("dim_test/processed_")
    assert key.endswith(".parquet")