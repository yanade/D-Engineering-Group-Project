import pandas as pd

from typing import Dict
import logging
from transformation.s3_client import S3TransformationClient
logger = logging.getLogger()
logger.setLevel(logging.INFO)


TRANSFORM_MAP = {
    "payment": ["make_fact_payment", "make_dim_date"],
    "sales_order": ["make_fact_sales_order", "make_dim_date"],
    "purchase_order": ["make_fact_purchase_order", "make_dim_date"],

    "currency": ["make_dim_currency"],
    "staff": ["make_dim_staff"],
    "address": ["make_dim_location"],
    "counterparty": ["make_dim_counterparty"],
    "design": ["make_dim_design"],
    "payment_type": ["make_dim_payment_type"],
    "transaction": ["make_dim_transaction"],
}


OUTPUT_NAME = {
    "make_dim_date": "dim_date",
    "make_fact_payment": "fact_payment",
    "make_fact_sales_order": "fact_sales_order",
    "make_fact_purchase_order": "fact_purchase_order",
    "make_dim_currency": "dim_currency",
    "make_dim_staff": "dim_staff",
    "make_dim_location": "dim_location",
    "make_dim_counterparty": "dim_counterparty",
    "make_dim_design": "dim_design",
    "make_dim_payment_type": "dim_payment_type",
    "make_dim_transaction": "dim_transaction",
}


class TransformService:
    """
    Transform service tightly coupled to S3TransformationClient
    """

    def __init__(self, ingest_bucket: str, processed_bucket: str):
        self.ingest_s3 = S3TransformationClient(ingest_bucket)
        self.processed_s3 = S3TransformationClient(processed_bucket)
        self._cache: Dict[str, pd.DataFrame] = {}
        logger.info(
            f"TransformService initialised. ingest={ingest_bucket}, processed={processed_bucket}")

    def _get_ingest_table(self, table_name: str) -> pd.DataFrame:
        if table_name not in self._cache:
            logger.info(f"Fetching ingest table: {table_name}")
            self._cache[table_name] = self.ingest_s3.read_table(table_name)
        return self._cache[table_name]

    # Dimensions
    def make_dim_currency(self) -> pd.DataFrame:
        logger.info("Creating dim_currency")
        currency = self._get_ingest_table("currency")
        currency = currency.drop_duplicates(
            subset=["currency_id"], keep="last")
        return currency[["currency_id", "currency_code"]]

    def make_dim_staff(self) -> pd.DataFrame:
        logger.info("Creating dim_staff")
        staff = self._get_ingest_table("staff").drop_duplicates(
            subset=["staff_id"], keep="last")
        department = self._get_ingest_table("department").drop_duplicates(
            subset=["department_id"], keep="last")
        dim = staff.join(department, on="department_id", rsuffix="_dept")
        return dim[
            [
                "staff_id",
                "first_name",
                "last_name",
                "department_name",
                "location",
                "email_address",
            ]
        ]

    def make_dim_location(self) -> pd.DataFrame:
        logger.info("Creating dim_location")
        address = self._get_ingest_table("address").drop_duplicates(
            subset=["address_id"], keep="last")
        dim_location = address.rename(columns={"address_id": "location_id"})
        return dim_location[
            [
                "location_id",
                "address_line_1",
                "address_line_2",
                "district",
                "city",
                "postal_code",
                "country",
                "phone",
            ]
        ]

    def make_dim_counterparty(self) -> pd.DataFrame:
        logger.info("Creating dim_counterparty")
        counterparty = self._get_ingest_table("counterparty").drop_duplicates(
            subset=["counterparty_id"], keep="last")
        address = (
            self._get_ingest_table("address")
            .drop_duplicates(subset=["address_id"], keep="last")
            .rename(columns={"address_id": "legal_address_id"})
            # added this line to get rid of Nan values
            .set_index("legal_address_id")
        )
        dim = counterparty.join(
            address,
            on="legal_address_id",
            rsuffix="_addr")
        return dim.rename(
            columns={
                "address_line_1": "counterparty_legal_address_line_1",
                "address_line_2": "counterparty_legal_address_line_2",
                "district": "counterparty_legal_district",
                "city": "counterparty_legal_city",
                "postal_code": "counterparty_legal_postal_code",
                "country": "counterparty_legal_country",
                "phone": "counterparty_legal_phone_number",
            }
        )[
            [
                "counterparty_id",
                "counterparty_legal_name",
                "counterparty_legal_address_line_1",
                "counterparty_legal_address_line_2",
                "counterparty_legal_district",
                "counterparty_legal_city",
                "counterparty_legal_postal_code",
                "counterparty_legal_country",
                "counterparty_legal_phone_number",
            ]
        ]

    def make_dim_design(self) -> pd.DataFrame:
        logger.info("Creating dim_design")
        design = self._get_ingest_table("design").drop_duplicates(
            subset=["design_id"], keep="last")
        return design[["design_id", "design_name",
                       "file_location", "file_name"]]

    def make_dim_payment_type(self) -> pd.DataFrame:
        logger.info("Creating dim_payment_type")
        payment_type = self._get_ingest_table("payment_type").drop_duplicates(
            subset=["payment_type_id"], keep="last")
        return payment_type[["payment_type_id", "payment_type_name"]]

    def make_dim_date(self) -> pd.DataFrame:
        logger.info("Creating dim_date")
        payments = self._get_ingest_table("payment")
        purchases = self._get_ingest_table("purchase_order")
        sales = self._get_ingest_table("sales_order")
        logger.info("Getting dates from payment")
        payment_dates = pd.melt(
            payments[["created_at", "last_updated", "payment_date"]]
        )["value"]
        logger.info("Getting dates from sales_order")
        sales_dates = pd.melt(
            sales[["created_at", "last_updated", "agreed_delivery_date", "agreed_payment_date"]]
        )["value"]
        logger.info("Getting dates from purchase_order")
        purchase_dates = pd.melt(
            purchases[["created_at", "last_updated", "agreed_delivery_date", "agreed_payment_date"]]
        )["value"]
        logger.info("Collating dates")
        total_dates = pd.concat(
            [payment_dates, sales_dates, purchase_dates], ignore_index=True)
        total_dates = pd.to_datetime(
            total_dates,
            format="mixed",
            errors="coerce",
            utc=True)
        total_dates = total_dates.dropna().dt.normalize().drop_duplicates().sort_values()
        dates = pd.DataFrame({"date": total_dates.dt.date})
        dt = pd.to_datetime(
            dates["date"],
            format="mixed",
            errors="coerce")  # guaranteed datetime64[ns]
        dates["year"] = dt.dt.year
        dates["month"] = dt.dt.month
        dates["day"] = dt.dt.day
        dates["day_of_week"] = dt.dt.day_of_week
        dates["day_name"] = dt.dt.day_name()
        dates["month_name"] = dt.dt.month_name()
        dates["quarter"] = dt.dt.quarter
        dates.insert(0, "date_id", range(1, len(dates) + 1))
        return dates

    def make_dim_transaction(self) -> pd.DataFrame:
        logger.info("Creating dim_transaction")
        txn = self._get_ingest_table("transaction").drop_duplicates(
            subset=["transaction_id"], keep="last")
        return txn[
            [
                "transaction_id",
                "transaction_type",
                "sales_order_id",
                "purchase_order_id",
            ]
        ]

        # Fact Tables
    def make_fact_sales_order(self) -> pd.DataFrame:
        table_name = "fact_sales_order"
        logger.info(f"Creating {table_name}")
        sales_order = self._get_ingest_table("sales_order")
        # source_count = len(sales_order)
        sales_order["created_date"] = pd.to_datetime(
            sales_order["created_at"], format="mixed", errors="coerce").dt.date
        sales_order["created_time"] = pd.to_datetime(
            sales_order["created_at"], format="mixed", errors="coerce").dt.time
        sales_order["last_updated_date"] = pd.to_datetime(
            sales_order["last_updated"], format="mixed", errors="coerce").dt.date
        sales_order["last_updated_time"] = pd.to_datetime(
            sales_order["last_updated"], format="mixed", errors="coerce").dt.time
        sales_order["agreed_payment_date"] = pd.to_datetime(
            sales_order["agreed_payment_date"], format="mixed", errors="coerce").dt.date
        sales_order["agreed_delivery_date"] = pd.to_datetime(
            sales_order["agreed_delivery_date"], format="mixed", errors="coerce").dt.date
        fact = sales_order[
            ["sales_order_id",
             "created_date",
             "created_time",
             "last_updated_date",
             "last_updated_time",
             "staff_id",
             "counterparty_id",
             "units_sold",
             "unit_price",
             "currency_id",
             "design_id",
             "agreed_payment_date",
             "agreed_delivery_date",
             "agreed_delivery_location_id",]
        ].rename(
            columns={
                "staff_id": "sales_staff_id",
                "counterparty_id": "sales_counterparty_id",
            })
        logger.info(
            f"Transformation successful: {table_name} rows={len(fact)}"
        )
        return fact

    def make_fact_payment(self) -> pd.DataFrame:
        logger.info("Creating fact_payment")
        payment = self._get_ingest_table("payment")
        payment["payment_date"] = pd.to_datetime(
            payment["payment_date"], format="mixed", errors="coerce").dt.date
        return payment[
            [
                "payment_id",
                "transaction_id",
                "counterparty_id",
                "payment_amount",
                "currency_id",
                "payment_type_id",
                "payment_date",
                "paid",
            ]
        ]

    def make_fact_purchase_order(self) -> pd.DataFrame:
        logger.info("Creating fact_purchase_order")
        po = self._get_ingest_table("purchase_order")
        # Parse timestamps
        po["created_at"] = pd.to_datetime(
            po["created_at"], format="mixed", errors="coerce")
        po["last_updated"] = pd.to_datetime(
            po["last_updated"], format="mixed", errors="coerce")
        # Split date/time (as your fact table shows created_date/created_time
        # etc.)
        po["created_date"] = po["created_at"].dt.date
        po["created_time"] = po["created_at"].dt.time
        po["last_updated_date"] = po["last_updated"].dt.date
        po["last_updated_time"] = po["last_updated"].dt.time
        # Ensure agreed dates are pure dates
        # po["agreed_delivery_date"] = pd.to_datetime(format="mixed", errors="coercepo["agreed_delivery_date"], errors="coerce").dt.date
        # po["agreed_payment_date"] = pd.to_datetime(format="mixed",
        # errors="coercepo["agreed_payment_date"], errors="coerce").dt.date
        po["agreed_payment_date"] = pd.to_datetime(
            po["agreed_payment_date"], format="mixed", errors="coerce").dt.date
        po["agreed_delivery_date"] = pd.to_datetime(
            po["agreed_delivery_date"], format="mixed", errors="coerce").dt.date
        fact = po[
            [
                "purchase_order_id",
                "created_date",
                "created_time",
                "last_updated_date",
                "last_updated_time",
                "staff_id",
                "counterparty_id",
                "item_code",
                "item_quantity",
                "item_unit_price",
                "currency_id",
                "agreed_delivery_date",
                "agreed_payment_date",
                "agreed_delivery_location_id",
            ]
        ]

        fact.insert(0, "purchase_record_id", range(1, len(fact) + 1))
        return fact

    # Orchestration

    def run(self):
        logger.info("Starting transformation run")
        logger.info(f"TRANSFORM_MAP contains: {list(TRANSFORM_MAP.keys())}")
        outputs = {
            "dim_transaction": self.make_dim_transaction(),
            "dim_staff": self.make_dim_staff(),
            "dim_payment_type": self.make_dim_payment_type(),
            "dim_location": self.make_dim_location(),
            "dim_design": self.make_dim_design(),
            "dim_date": self.make_dim_date(),
            "dim_currency": self.make_dim_currency(),
            "dim_counterparty": self.make_dim_counterparty(),
            "fact_sales_order": self.make_fact_sales_order(),
            "fact_purchase_orders": self.make_fact_purchase_order(),
            "fact_payment": self.make_fact_payment(),
        }

        logger.info(f"Generated {len(outputs)} tables: {list(outputs.keys())}")

        for name, df in outputs.items():
            logger.info(f"Writing {name} ({len(df)} rows)")
            if df is not None and len(df) > 0:
                self.processed_s3.write_parquet(name, df)
            else:
                logger.warning(f"{name} is empty or None, skipping")
            self.processed_s3.write_parquet(name, df)
        logger.info("Transformation run completed successfully")

    def run_single_table(self, table_name: str):
        logger.info(f"Running single-table transformation for '{table_name}'")

        methods = TRANSFORM_MAP.get(table_name)
        if not methods:
            logger.warning(f"No transformation mapped for '{table_name}'")
            return {
                "table": table_name,
                "status": "skipped",
                "reason": "no_transform_defined"}

        results = []

        for method_name in methods:
            transform_method = getattr(self, method_name)
            df = transform_method()

            output_name = OUTPUT_NAME.get(method_name, method_name)
            logger.info(
                f"Writing '{output_name}' from '{method_name}' ({
                    len(df)} rows)")
            s3_key = self.processed_s3.write_parquet(output_name, df)

            results.append({
                "method": method_name,
                "output": output_name,
                "rows": len(df),
                "s3_key": s3_key,
            })

        return {"table": table_name, "status": "success", "results": results}
