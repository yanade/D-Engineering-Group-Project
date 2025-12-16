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
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            s3_key = self.s3.write_json(table_name, raw_payload)

            logger.info(f"Ingestion preview complete for table '{table_name}'. " f"Uploaded to S3 key: {s3_key}")

            # RETURN METADATA ONLY (no heavy payload)
            return {
                "table": table_name,
                "row_count": len(rows),
                "s3_key": s3_key,
                "timestamp": raw_payload["timestamp"],
            }

        except Exception as e:
            logger.exception(f"Ingestion preview FAILED for table '{table_name}'. Error: {e}")
            raise

    def ingest_table_changes(self, table_name: str):
        logger.info(f"Starting incremental ingestion for table '{table_name}'")

        try:
            # Get last checkpoint from S3
            last_checkpoint = self.s3.get_checkpoint(table_name)

            # Fetch new/updated rows from DB since last checkpoint
            changes = self.db.fetch_changes(table_name, since=last_checkpoint)

            logger.info(f"Fetched {len(changes)} changed rows from table '{table_name}' since '{last_checkpoint}'")
            if not changes:
                logger.info(f"No new changes found for table '{table_name}'. Skipping S3 upload.")
                return {
                    "table": table_name,
                    "row_count": 0,
                    "s3_key": None,
                    "status": "no_changes",
                }

            s3_key = self.s3.write_json(table_name=table_name, data=changes)

            logger.info(f"Incremental ingestion complete for table '{table_name}'. " f"Uploaded to S3 key: {s3_key}")

            timestamp_col = self.db.infer_timestamp_column(table_name)
            if timestamp_col is not None:
                raw_checkpoint = max(row[timestamp_col] for row in changes)
                if isinstance(raw_checkpoint, str):
                    new_checkpoint = datetime.fromisoformat(raw_checkpoint)
                else:
                    new_checkpoint = raw_checkpoint
                self.s3.write_checkpoint(table_name, timestamp=new_checkpoint)
                logger.info(f"Updated checkpoint for table '{table_name}' to '{new_checkpoint}'")
                checkpoint_str = new_checkpoint.isoformat()
            else:
                checkpoint_str = None
                logger.info(f"[{table_name}] No timestamp column found; checkpoint not updated.")

            # RETURN METADATA ONLY (no heavy payload)
            return {
                "table": table_name,
                "row_count": len(changes),
                "s3_key": s3_key,
                "checkpoint": checkpoint_str,
            }

        except Exception as e:
            logger.exception(f"Incremental ingestion FAILED for table '{table_name}'. Error: {e}")
            raise

    def ingest_all_tables(self, tables: list[str] | None = None, limit: int = 50):
        """
        Ingests new rows from all tables in the database.
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
                # CHANGED LINE 142
                result = self.ingest_table_changes(table)
                results[table] = {"status": "success", **result}

            except Exception as e:
                logger.error(f"Failed to ingest table '{table}'")
                results[table] = {"status": "error", "error": str(e)}

        logger.info("All-table ingestion completed.")
        return results

    def close(self):
        logger.info("Closing IngestionService resources...")
        self.db.close()
