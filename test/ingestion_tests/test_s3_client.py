import os
from src.ingestion.s3_client import S3Client
from datetime import datetime, timezone
from moto import mock_aws
import boto3
import json
import pytest


def test_s3_client_initialises_correctly():
    client = S3Client(bucket="test-bucket")

    assert client.bucket == "test-bucket"
    assert client.s3 is not None


@mock_aws
def test_write_json_uploads_data_to_s3():

    s3 = boto3.client("s3", region_name="eu-west-2")
    s3.create_bucket(Bucket="test-bucket", CreateBucketConfiguration={"LocationConstraint": "eu-west-2"})

    client = S3Client(bucket="test-bucket")

    data = [{"id": 1, "name": "Yana"}]

    key = client.write_json("staff", data)

    response = s3.get_object(Bucket="test-bucket", Key=key)
    body = json.loads(response["Body"].read().decode("utf-8"))

    assert body == data


def test_write_json_raises_error_when_s3_fails(mocker):
    client = S3Client(bucket="test-bucket")

    mocker.patch.object(client.s3, "put_object", side_effect=Exception("Upload failed"))

    with pytest.raises(Exception) as exc:
        client.write_json("staff", [{"id": 1}])

    assert "Upload failed" in str(exc.value)


def test_write_json_key_format(mocker):
    client = S3Client(bucket="test-bucket")

    class FakeDatetime:
        @staticmethod
        def now(tz=None):

            return datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    mocker.patch("src.ingestion.s3_client.datetime", FakeDatetime)

    mocker.patch.object(client.s3, "put_object")

    key = client.write_json("staff", [])

    assert key.startswith("staff/raw_2025-01-01T12-00-00")
