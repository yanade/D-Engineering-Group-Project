from db_client import DatabaseClient
from s3_client import S3Client
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



    def ingest_all_tables(self, tables: list[str] | None = None, limit: int = 50):
        """
        Ingests preview rows from all tables in the database.
        """
        tables_to_process = tables or self.db.list_tables()
        logger.info(f"Starting ingestion for {len(tables_to_process)} tables")

        results = {}

        for table in tables_to_process:
            logger.info(f"Processing table '{table}'")
            if table == "_prisma_migrations":
                logger.info(f"Skipping internal table '{table}'")
                continue

            try:
                result = self.ingest_table_preview(table, limit)
                results[table] = {"status": "success", **result}

            except Exception as e:
                logger.error(f"Failed to ingest table '{table}'")
                results[table] = {"status": "error", "error": str(e)}

        logger.info("All-table ingestion completed.")
        return results

    def close(self):
        logger.info("Closing IngestionService resources...")
        self.db.close()

    def close(self):
        logger.info("Closing IngestionService resources...")
        self.db.close()