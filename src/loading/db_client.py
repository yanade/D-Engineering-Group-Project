import json
import logging
import os
from typing import List, Dict, Any

import boto3
import pg8000.native

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class WarehouseDBClient:
    """Client for connecting to the data warehouse RDS instance."""

    def __init__(self):
        logger.info("Initializing WarehouseDBClient...")

        secret_arn = os.getenv("DW_SECRET_ARN")
        if not secret_arn:
            raise ValueError("DW_SECRET_ARN environment variable is required")

        client = boto3.client("secretsmanager")
        response = client.get_secret_value(SecretId=secret_arn)
        secret = json.loads(response["SecretString"])

        self.conn = pg8000.native.Connection(
            host=secret["host"],
            port=secret["port"],
            database=secret["database"],
            user=secret["username"],
            password=secret["password"],
            timeout=10,
        )

        logger.info("Warehouse connection established")

    def create_tables(self):
        logger.info("Creating warehouse tables...")
        
        # SQL for creating tables
        create_sql = [
            # Dimension Tables
            """
            CREATE TABLE IF NOT EXISTS dim_currency (
                currency_id INT PRIMARY KEY,
                currency_code VARCHAR(10) NOT NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS dim_staff (
                staff_id INT PRIMARY KEY,
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                department_name VARCHAR(255),
                location VARCHAR(255),
                email_address VARCHAR(255)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS dim_location (
                location_id INT PRIMARY KEY,
                address_line_1 VARCHAR(255),
                address_line_2 VARCHAR(255),
                district VARCHAR(255),
                city VARCHAR(255),
                postal_code VARCHAR(20),
                country VARCHAR(100),
                phone VARCHAR(50)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS dim_counterparty (
                counterparty_id INT PRIMARY KEY,
                counterparty_legal_name VARCHAR(255),
                counterparty_legal_address_line_1 VARCHAR(255),
                counterparty_legal_address_line_2 VARCHAR(255),
                counterparty_legal_district VARCHAR(255),
                counterparty_legal_city VARCHAR(255),
                counterparty_legal_postal_code VARCHAR(20),
                counterparty_legal_country VARCHAR(100),
                counterparty_legal_phone_number VARCHAR(50)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS dim_design (
                design_id INT PRIMARY KEY,
                design_name VARCHAR(255),
                file_location VARCHAR(255),
                file_name VARCHAR(255)
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS dim_date (
                date_id INT PRIMARY KEY,
                date DATE NOT NULL,
                year INT NOT NULL,
                month INT NOT NULL,
                day INT NOT NULL,
                day_of_week INT NOT NULL,
                day_name VARCHAR(20) NOT NULL,
                month_name VARCHAR(20) NOT NULL,
                quarter INT NOT NULL,
                UNIQUE(date)
            );
            """,
            # Fact Tables (with history tracking)
            """
            CREATE TABLE IF NOT EXISTS fact_sales_order (
                sales_record_id SERIAL PRIMARY KEY,
                sales_order_id INT NOT NULL,
                created_date DATE NOT NULL,
                created_time TIME NOT NULL,
                last_updated_date DATE NOT NULL,
                last_updated_time TIME NOT NULL,
                sales_staff_id INT REFERENCES dim_staff(staff_id),
                sales_counterparty_id INT REFERENCES dim_counterparty(counterparty_id),
                units_sold INT,
                unit_price DECIMAL(10,2),
                currency_id INT REFERENCES dim_currency(currency_id),
                design_id INT REFERENCES dim_design(design_id),
                agreed_payment_date DATE,
                agreed_delivery_date DATE,
                agreed_delivery_location_id INT REFERENCES dim_location(location_id),
                valid_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                valid_to TIMESTAMP DEFAULT '9999-12-31',
                is_current BOOLEAN DEFAULT TRUE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS fact_purchase_order (
                purchase_record_id SERIAL PRIMARY KEY,
                purchase_order_id INT NOT NULL,
                created_date DATE NOT NULL,
                created_time TIME NOT NULL,
                last_updated_date DATE NOT NULL,
                last_updated_time TIME NOT NULL,
                staff_id INT REFERENCES dim_staff(staff_id),
                counterparty_id INT REFERENCES dim_counterparty(counterparty_id),
                item_code VARCHAR(50),
                item_quantity INT,
                item_unit_price DECIMAL(10,2),
                currency_id INT REFERENCES dim_currency(currency_id),
                agreed_delivery_date DATE,
                agreed_payment_date DATE,
                agreed_delivery_location_id INT REFERENCES dim_location(location_id),
                valid_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                valid_to TIMESTAMP DEFAULT '9999-12-31',
                is_current BOOLEAN DEFAULT TRUE
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS fact_payment (
                payment_id INT PRIMARY KEY,
                transaction_id INT,
                counterparty_id INT REFERENCES dim_counterparty(counterparty_id),
                payment_amount DECIMAL(10,2),
                currency_id INT REFERENCES dim_currency(currency_id),
                payment_type_id INT,
                payment_date DATE,
                paid BOOLEAN
            );
            """
        ]
        
        for sql in create_sql:
            self.conn.run(sql)

        logger.info("Warehouse tables created")

    def upsert_dimension(self, table_name: str, data: List[Dict[str, Any]]):
        if not data:
            return

        columns = list(data[0].keys())
        placeholders = ", ".join([f"${i+1}" for i in range(len(columns))])
        col_names = ", ".join(columns)

        pk_column = columns[0]
        update_cols = ", ".join(
            f"{col} = EXCLUDED.{col}" for col in columns[1:]
        )

        sql = f"""
            INSERT INTO {table_name} ({col_names})
            VALUES ({placeholders})
            ON CONFLICT ({pk_column})
            DO UPDATE SET {update_cols}
        """

        try:
            # Insert each row with named parameters
            for i, row in enumerate(data):
                if i % 100 == 0:  # Log progress every 100 rows
                    logger.debug(f"Processing row {i+1}/{len(data)}")
                
                # Convert row to parameter dictionary
                params = {col: row[col] for col in columns}
                self.conn.run(sql, **params)
            
            logger.info(f" Upserted {len(data)} rows into {table_name}")
            
        except Exception as e:
            logger.exception(f" Failed to upsert {table_name}: {e}")
            try:
                self.conn.run("ROLLBACK")
            except:
                pass
            raise

    def insert_fact_with_history(self, table_name: str, data: List[Dict[str, Any]]):
        if not data:
            return

        columns = list(data[0].keys())
        placeholders = ", ".join([f"${i+1}" for i in range(len(columns))])
        col_names = ", ".join(columns)

        sql = f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})"

        try:
            # Insert each row with named parameters
            for i, row in enumerate(data):
                if i % 100 == 0:  # Log progress every 100 rows
                    logger.debug(f"Processing row {i+1}/{len(data)}")
                
                # Convert row to parameter dictionary
                params = {col: row[col] for col in columns}
                self.conn.run(sql, **params)
            
            logger.info(f" Upserted {len(data)} rows into {table_name}")
            
        except Exception as e:
            logger.exception(f" Failed to upsert {table_name}: {e}")
            try:
                self.conn.run("ROLLBACK")
            except:
                pass
            raise

    def close(self):
        if self.conn:
            self.conn.close()