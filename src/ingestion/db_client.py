from dotenv import load_dotenv
from pg8000.native import Connection
from datetime import datetime
import os
import logging
import boto3
import json
import sys


logger = logging.getLogger()
logger.setLevel(logging.INFO)
print(f"DEBUG: Python path: {sys.path}")
print(f"DEBUG: Current directory: {os.getcwd()}")
print(f"DEBUG: Environment variables: {dict(os.environ)}")
load_dotenv()


class DatabaseClient:
    def __init__(self):
        logger.info("Initializing DatabaseClient...")
        # Check if running locally (with .env) or in Lambda (with Secrets Manager)
        if os.path.exists(".env") or all(
            [
                os.getenv("DB_HOST"),
                os.getenv("DB_NAME"),
                os.getenv("DB_USER"),
                os.getenv("DB_PASSWORD"),
            ]
        ):
            # Local development or test environment
            self.host = os.getenv("DB_HOST")
            self.database = os.getenv("DB_NAME")
            self.user = os.getenv("DB_USER")
            self.password = os.getenv("DB_PASSWORD")
            self.port = int(os.getenv("DB_PORT", 5432))
            logger.info("Using environment variables for DB connection")
        else:
            # Lambda environment - use Secrets Manager
            secret_arn = os.getenv("DB_SECRET_ARN")
            if not secret_arn:
                raise ValueError("DB_SECRET_ARN environment variable is required in Lambda")
            client = boto3.client("secretsmanager")
            response = client.get_secret_value(SecretId=secret_arn)
            secret = json.loads(response["SecretString"])
            self.host = secret.get("host")
            self.database = secret.get("database")
            self.user = secret.get("username")
            self.password = secret.get("password")
            self.port = int(secret.get("port", 5432))
            logger.info("Using Secrets Manager for DB connection")
        logger.info("Loaded DB env variables")
        if not all([self.host, self.database, self.user, self.password, self.port]):
            logger.error("Missing required DB environment variables!")
            raise ValueError("One or more database environment variables are missing.")
        try:
            self.conn = Connection(
                user=self.user,
                host=self.host,
                database=self.database,
                password=self.password,
                port=self.port,
            )
            logger.info("Database connection successfully.")
        except Exception as e:
            logger.exception(f"Failed to database connection: {e}")
            raise

    def run(self, sql: str, params: dict | None = None):
        logger.info(f"Executing SQL: {sql} | params={params}")
        try:
            if params:
                rows = self.conn.run(sql, **params)
            else:
                rows = self.conn.run(sql)
            column_names = [col["name"] for col in self.conn.columns]
            result = [dict(zip(column_names, row)) for row in rows]
            logger.info(f"SQL executed successfully. Returned {len(result)} rows.")
            return result
        except Exception as e:
            logger.exception(f"Error executing SQL: {sql}, {e}")
            raise

    def fetch_preview(self, table_name: str, limit: int = 10):
        logger.info(f"Fetching preview from table '{table_name}' (limit={limit})")
        if not table_name.isidentifier():
            raise ValueError(f"Unsafe table name: {table_name}")
        sql = f"SELECT * FROM {table_name} LIMIT :limit"
        rows = self.run(sql, {"limit": limit})
        if not rows:
            return {"columns": [], "rows": []}
        return {"columns": list(rows[0].keys()), "rows": rows}

    def list_tables(self):
        """
        Returns a list of all user tables in the public schema.
        """
        sql = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """

        try:
            rows = self.run(sql)
            table_names = [row["table_name"] for row in rows]
            logger.info(f"Found {len(table_names)} tables: {table_names}")
            return table_names

        except Exception:
            logger.exception("Failed to list tables from information_schema")
            raise

    def get_columns(self, table_name: str):
        """
        Returns a list of column names for the specified table.
        """
        if not table_name.isidentifier():
            raise ValueError(f"Unsafe table name: {table_name}")

        sql = """
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = :table_name
            ORDER BY ordinal_position;
        """

        try:

            rows = self.run(sql, {"table_name": table_name})
            # expected format output [{"column_name": "staff_id", "data_type": "integer"}]

            logger.info(f"Columns for table '{table_name}': {rows}")
            return rows

        except Exception as e:
            logger.exception(f"Failed to get columns for table '{table_name}', {e}")
            raise

    def infer_timestamp_column(self, table_name: str):
        """
        Detects the most appropriate timestamp column for incremental ingestion.
        Returns the column name or None if not found.
        """
        try:
            columns = self.get_columns(table_name)

            timestamp_candidates = [col["column_name"] for col in columns if "timestamp" in col["data_type"].lower()]
            date_candidates = [col["column_name"] for col in columns if "date" in col["data_type"].lower()]
            preferred_names = [
                "last_updated",
                "updated_at",
                "created_at",
                "modified_at",
            ]

            for pref in preferred_names:
                for candidate in timestamp_candidates:
                    if candidate.lower() == pref:
                        logger.info(f"[{table_name}] Using preferred timestamp column: {candidate}")
                        return candidate

            if timestamp_candidates:
                logger.info(f"[{table_name}] Using first timestamp column: {timestamp_candidates[0]}")
                return timestamp_candidates[0]

            if date_candidates:
                logger.warning(
                    f"[{table_name}] No timestamp columns found, using DATE column '{date_candidates[0]}' "
                    f"(incremental ingestion may be less accurate)"
                )
                return date_candidates[0]

            logger.warning(f"[{table_name}] No timestamp/date columns found.")
            return None
        except Exception as e:
            logger.exception(f"Failed to infer timestamp column for table '{table_name}','{e}'")
            raise

    def fetch_changes(self, table_name: str, since: datetime | None = None):
        """
        Fetches new or updated rows from the table since the given checkpoint timestamp.
        """

        logger.info(f"Fetching incremental data from '{table_name}' since '{since}'")

        if not table_name.isidentifier():
            raise ValueError(f"Unsafe table name: {table_name}")

        timestamp_col = self.infer_timestamp_column(table_name)

        if timestamp_col is None:
            logger.warning(f"[{table_name}] No timestamp column found → FULL table ingestion.")
            return self.run(f"SELECT * FROM {table_name};")

        if since is None:
            logger.info(f"[{table_name}] No checkpoint found → FULL table ingestion.")
            return self.run(f"SELECT * FROM {table_name};")

        sql = f"""
            SELECT *
            FROM {table_name}
            WHERE {timestamp_col} > :since
            ORDER BY {timestamp_col} ASC;
        """

        try:
            rows = self.run(sql, {"since": since})
            logger.info(f"Fetched {len(rows)} incremental rows from '{table_name}'")
            return rows

        except Exception as e:
            logger.exception(f"Failed to fetch incremental data from table '{table_name}','{e}'")
            raise

    def close(self):
        try:
            self.conn.close()
            logger.info("Database connection closed.")
        except Exception as e:
            logger.warning(f"Failed to close database connection cleanly: {e}")
