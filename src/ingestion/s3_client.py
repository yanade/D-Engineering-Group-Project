import boto3
import json
from datetime import datetime, timezone
import logging


logger = logging.getLogger()
logger.setLevel(logging.INFO)


class S3Client:
    """
    Raw ingestion layer
    """
    def __init__(self, bucket: str):
        self.bucket = bucket
        self.s3 = boto3.client("s3")

        logger.info(f"S3Client initialised with bucket: {bucket}")

    def write_json(self, table_name: str, data: list[dict]):
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
        key = f"{table_name}/raw_{timestamp}.json"
        logger.info(
            f"Uploading JSON to S3 → bucket={self.bucket}, key={key}, rows={len(data)}"
        )

        try:
            self.s3.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=json.dumps(data, default=str)
            )

            logger.info(f"S3 upload successful → s3://{self.bucket}/{key}")
            return key
        
        except Exception as e:
            logger.exception(f"Failed to upload JSON to S3 (bucket={self.bucket}, key={key})")
            raise