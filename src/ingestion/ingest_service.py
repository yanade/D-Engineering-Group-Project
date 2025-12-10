from src.ingestion.db_client import DatabaseClient
from src.ingestion.s3_client import S3Client
from datetime import datetime, timezone
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
        self.db = DatabaseClient()
        self.s3 = S3Client(bucket)

    def ingest_table_preview(self, table_name: str, limit: int = 10):
        logger.info(f"Starting ingestion preview for table '{table_name}', limit={limit}")

        try:
            # DB fetch MUST return {'columns': [...], 'rows': [...]}
            preview = self.db.fetch_preview(table_name, limit)
            columns = preview["columns"]
            rows = preview["rows"]

            logger.info(f"Fetched {len(rows)} rows from table '{table_name}'")

            # RAW PAYLOAD written to S3
            raw_payload = {
                "table": table_name,
                "columns": columns,
                "rows": rows,
                "limit": limit,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            s3_key = self.s3.write_json(table_name, raw_payload)

            logger.info(
                f"Ingestion preview complete for table '{table_name}'. "
                f"Uploaded to S3 key: {s3_key}"
            )

            # RETURN METADATA ONLY (no heavy payload)
            return {
                "table": table_name,
                "row_count": len(rows),
                "s3_key": s3_key,
                "timestamp": raw_payload["timestamp"]
            }

        except Exception as e:
            logger.exception(f"Ingestion preview FAILED for table '{table_name}'. Error: {e}")
            raise

    def close(self):
        logger.info("Closing IngestionService resources...")
        self.db.close()