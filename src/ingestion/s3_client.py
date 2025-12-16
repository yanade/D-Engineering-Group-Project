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
                Bucket=self.bucket, Key=key, Body=json.dumps(data, default=str)
            )

            logger.info(f"S3 upload successful → s3://{self.bucket}/{key}")
            return key

        except Exception as e:
            logger.exception(
                f"Failed to upload JSON to S3 (bucket={self.bucket}, key={key}, {e})"
            )
            raise

    def get_checkpoint(self, table_name: str):
        """
        Returns last_ingested datetime for a table, or None if checkpoint does not exist.
        """
        key = f"checkpoints/{table_name}_checkpoint.json"
        try:
            response = self.s3.get_object(Bucket=self.bucket, Key=key)
            body = response["Body"].read().decode("utf-8")
            data = json.loads(body)
            checkpoint = datetime.fromisoformat(data["last_ingested"])
            logger.info(f"Retrieved checkpoint for table '{table_name}': {checkpoint}")
            return checkpoint
        except self.s3.exceptions.NoSuchKey:
            logger.info(f"No checkpoint found for table '{table_name}'")
            return None
        except Exception as e:
            logger.exception(f"Failed to retrieve checkpoint for table '{table_name}', {e}")
            raise

    def write_checkpoint(self, table_name: str, timestamp: datetime):
        """
        Writes the last_ingested datetime for a table checkpoint.
        """

        if not isinstance(timestamp, datetime):
            raise ValueError("Checkpoint timestamp must be a datetime object")

        key = f"checkpoints/{table_name}_checkpoint.json"
        data = {
            "table": table_name,
            "last_ingested": timestamp.astimezone(timezone.utc).isoformat(),
        }
        logger.info(
            f"Saving checkpoint for table '{table_name}': {data['last_ingested']}"
        )

        try:
            self.s3.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=json.dumps(data),
                ContentType="application/json",
            )
            logger.info(
                f"Wrote checkpoint for table '{table_name}': {data['last_ingested']}"
            )

        except Exception as e:
            logger.exception(f"Failed to write checkpoint for table '{table_name}', {e}")
            raise
