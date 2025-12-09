from src.ingestion.db_client import DatabaseClient
from src.ingestion.s3_client import S3Client
import logging



logger = logging.getLogger()
logger.setLevel(logging.INFO)




class IngestionService:
    """
    - reading from db
    - writing raw data into S3
    """

    def __init__(self, bucket: str):
        logger.info(f"Initialising IngestionService with bucket={bucket}")

        self.bucket = bucket
        self.bucket = bucket
        self.db = DatabaseClient()
        self.s3 = S3Client(bucket)

    def ingest_table_preview(self, table_name: str, limit=10):
        logger.info(f"Starting ingestion preview for table '{table_name}', limit={limit}")
        try:
            rows = self.db.fetch_preview(table_name, limit)
            logger.info(f"Fetched {len(rows)} rows from table '{table_name}'")

            s3_key = self.s3.write_json(table_name, rows)
            logger.info(
                f"Ingestion preview complete for table '{table_name}'. "
                f"Uploaded to S3 key: {s3_key}"
            )

            return {"table": table_name, "rows": len(rows), "s3_key": s3_key}
        except Exception as e:
            logger.exception(f"Ingestion prewiew FAILED for table '{table_name}'.")

    def close(self):
        logger.info("Closing IngestionService resources...")
        self.db.close()