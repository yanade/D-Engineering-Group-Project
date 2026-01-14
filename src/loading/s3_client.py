import boto3
import pandas as pd
from io import BytesIO
import logging
from botocore.config import Config

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class S3LoaderClient:
    def __init__(self, bucket: str):
        self.bucket = bucket
        self.s3 = boto3.client(
            "s3",
            config=Config(
                connect_timeout=5,
                read_timeout=10,
                retries={"max_attempts": 2}
            )
        )
        logger.info(f"S3LoaderClient initialized for bucket: {bucket}")

    def read_latest_parquet(self, table_prefix: str) -> pd.DataFrame:
        prefix = f"{table_prefix}/"
        logger.info(f"Looking for latest Parquet under prefix: {prefix}")

        response = self.s3.list_objects_v2(
            Bucket=self.bucket,
            Prefix=prefix,
            MaxKeys=10
        )

        contents = response.get("Contents", [])

        if not contents:
            raise FileNotFoundError(f"No objects found under {prefix}")

        parquet_files = [
            obj for obj in contents if obj["Key"].endswith(".parquet")
        ]

        if not parquet_files:
            raise FileNotFoundError(f"No parquet files under {prefix}")

        parquet_files.sort(key=lambda x: x["LastModified"], reverse=True)
        latest_key = parquet_files[0]["Key"]

        logger.info(f"Reading Parquet: {latest_key}")
        return self.read_parquet(latest_key)

    def read_parquet(self, key: str) -> pd.DataFrame:
        obj = self.s3.get_object(Bucket=self.bucket, Key=key)
        buffer = BytesIO(obj["Body"].read())
        return pd.read_parquet(buffer)
