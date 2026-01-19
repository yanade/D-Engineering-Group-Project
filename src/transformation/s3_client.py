import json
import boto3
import pandas as pd
from uuid import uuid4
from io import BytesIO
from datetime import datetime, timezone
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class S3TransformationClient:
    def __init__(self, bucket: str):
        self.bucket = bucket
        self.s3 = boto3.client("s3")
        logger.info(f"Initialising S3 client. Raw data:  {self.bucket}")

    def read_json(self, key: str):
        logger.info(f"Reading raw JSON from s3://{self.bucket}/{key}")
        obj = self.s3.get_object(Bucket=self.bucket, Key=key)
        raw_data = obj["Body"].read().decode("utf-8")
        return json.loads(raw_data)

    def read_table(self, table_name: str) -> pd.DataFrame:
        """
        Reads ALL raw_*.json files for a table and returns a DataFrame.
        """
        prefix = f"{table_name}/"
        response = self.s3.list_objects_v2(
            Bucket=self.bucket,
            Prefix=prefix,
        )
        if "Contents" not in response:
            raise FileNotFoundError(f"No raw data for table '{table_name}'")
        rows: list[dict] = []
        for obj in response["Contents"]:
            key = obj["Key"]
            if not key.endswith(".json"):
                continue
            rows.extend(self.read_json(key))
        if not rows:
            raise ValueError(f"No rows found for table '{table_name}'")
        return pd.DataFrame(rows)

   


    def write_parquet(self, table_name: str, df: pd.DataFrame):
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        run_id= uuid4().hex
        key = f"{table_name}/processed_{timestamp}_{run_id}.parquet"
        # key = f"{table_name}/latest.parquet"
        buffer = BytesIO()
        df.to_parquet(buffer, index=False)
        buffer.seek(0)
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=buffer.read())
        logger.info(f"Parquet written → s3://{self.bucket}/{key}")
        return key
