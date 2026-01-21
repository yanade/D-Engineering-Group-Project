import logging
import os
from io import BytesIO
from typing import List, Optional
import pandas as pd
import boto3



logger = logging.getLogger(__name__)
logger.setLevel(os.getenv("LOG_LEVEL", "INFO"))

class S3LoadingClient:
    def __init__(self, bucket: str):
        self.bucket_name = bucket
        self.s3 = boto3.client("s3")
        logger.info("Initialising S3LoadingClient. bucket=%s", self.bucket_name)

    def list_parquet_keys(self, table_name: str) -> List[str]:


        # Returns parquet keys under: <table_name>/
        # Sorted by LastModified ascending (oldest -> newest).

        prefix = f"{table_name}/"
        paginator = self.s3.get_paginator("list_objects_v2")
        objects = []
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
            objects.extend(page.get("Contents", []))


        parquet_objects = [
            obj for obj in objects
            if obj["Key"].endswith(".parquet")
            and not obj["Key"].endswith("/")]

        sorted_objects = sorted(parquet_objects, key=lambda x: x["LastModified"])
        keys = [obj["Key"] for obj in sorted_objects]
        logger.info("Found %s parquet files under prefix=%s in bucket=%s", len(keys), prefix, self.bucket_name)
        
        return keys
    
    def read_parquet_to_df(self, key: str) -> pd.DataFrame:
        logger.info("Reading parquet from s3://%s/%s", self.bucket_name, key)
        response = self.s3.get_object(Bucket=self.bucket_name, Key=key)
        body_bytes = response["Body"].read()
        buffer = BytesIO(body_bytes)
        
        df = pd.read_parquet(buffer)
        logger.info("Loaded parquet rows=%s cols=%s key=%s", len(df), len(df.columns), key)
        return df
    
    def read_latest_parquet(self, table_name: str) -> Optional[pd.DataFrame]:
        #find latest parqet file for a table and read it to df

        keys = self.list_parquet_keys(table_name)
        if not keys:
            logger.warning("No parquet files found for table '%s'", table_name)
            return None

        latest_key = keys[-1]
        return self.read_parquet_to_df(latest_key)
