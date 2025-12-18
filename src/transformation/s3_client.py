import json
import boto3
import os
import pandas as pd
# import pyarrow.parquet as pq
import io 
from io import BytesIO
from datetime import datetime, timezone
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class S3TransformationClient:
    def __init__(self, bucket: str):
        self.bucket = bucket
        self.s3 = boto3.client("s3")
        logger.info(f"Initialising S3 claas . Raw data:  {self.bucket}")

    def read_json(self, key: str):
        logger.info(f"Reading raw JSON from s3://{self.bucket}/{key}")
        obj = self.s3.get_object(Bucket=self.bucket, Key=key)
        raw_data = obj["Body"].read().decode("utf-8")
        return json.loads(raw_data)
    
    def read_table(self, table_name: str) -> pd.DataFrame:
        """
        Reads s3://<bucket>/<table_name>.json and returns as a DataFrame.
        Assumes JSON is list[dict].
        """
        key = f"{table_name}.json"
        data = self.read_json(key)

        if isinstance(data, dict) and "data" in data:
            data = data["data"]

        return pd.DataFrame(data)

    def write_parquet(self, table_name: str, df: pd.DataFrame):
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
        key = f"{table_name}/processed_{timestamp}.parquet"
        buffer = BytesIO()
        df.to_parquet(buffer, index=False)
        buffer.seek(0)
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=buffer.read())
        logger.info(f"Parquet written → s3://{self.bucket}/{key}")
        return key
