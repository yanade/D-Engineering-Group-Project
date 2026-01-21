# src/loading/sql.py

CREATE_TABLE_SQL = {
    "dim_date": """
    CREATE TABLE IF NOT EXISTS dim_date (
        date_id INTEGER PRIMARY KEY,
        date DATE NOT NULL UNIQUE,
        year INTEGER NOT NULL,
        month INTEGER NOT NULL,
        day INTEGER NOT NULL,
        day_of_week INTEGER NOT NULL,
        day_name TEXT NOT NULL,
        month_name TEXT NOT NULL,
        quarter INTEGER NOT NULL CHECK (quarter BETWEEN 1 AND 4)
    );
    """,

    "dim_staff": """
    CREATE TABLE IF NOT EXISTS dim_staff (
        staff_id INTEGER PRIMARY KEY,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        department_name TEXT NOT NULL,
        location TEXT NOT NULL,
        email_address TEXT UNIQUE
    );
    """,

    "dim_counterparty": """
    CREATE TABLE IF NOT EXISTS dim_counterparty (
        counterparty_id INTEGER PRIMARY KEY,
        counterparty_legal_name TEXT NOT NULL,
        counterparty_legal_address_line_1 TEXT,
        counterparty_legal_address_line_2 TEXT,
        counterparty_legal_district TEXT,
        counterparty_legal_city TEXT,
        counterparty_legal_postal_code TEXT,
        counterparty_legal_country TEXT,
        counterparty_legal_phone_number TEXT
    );
    """,

    "dim_currency": """
    CREATE TABLE IF NOT EXISTS dim_currency (
        currency_id INTEGER PRIMARY KEY,
        currency_code TEXT NOT NULL UNIQUE
    );
    """,

    "dim_design": """
    CREATE TABLE IF NOT EXISTS dim_design (
        design_id INTEGER PRIMARY KEY,
        design_name TEXT NOT NULL,
        file_location TEXT,
        file_name TEXT
    );
    """,

    "dim_location": """
    CREATE TABLE IF NOT EXISTS dim_location (
        location_id INTEGER PRIMARY KEY,
        address_line_1 TEXT NOT NULL,
        address_line_2 TEXT,
        district TEXT,
        city TEXT NOT NULL,
        postal_code TEXT,
        country TEXT NOT NULL,
        phone TEXT
    );
    """,

    "dim_payment_type": """
    CREATE TABLE IF NOT EXISTS dim_payment_type (
        payment_type_id INTEGER PRIMARY KEY,
        payment_type_name TEXT NOT NULL UNIQUE
    );
    """,

    "dim_transaction": """
    CREATE TABLE IF NOT EXISTS dim_transaction (
        transaction_id INTEGER PRIMARY KEY,
        transaction_type TEXT NOT NULL,
        sales_order_id INTEGER,
        purchase_order_id INTEGER
    );
    """,

    "fact_sales_order": """
    CREATE TABLE IF NOT EXISTS fact_sales_order (
        sales_order_id INTEGER PRIMARY KEY,
        created_date DATE,
        created_time TIME,
        last_updated_date DATE,
        last_updated_time TIME,
        sales_staff_id INTEGER NOT NULL,
        sales_counterparty_id INTEGER NOT NULL,
        design_id INTEGER NOT NULL,
        currency_id INTEGER NOT NULL,
        agreed_delivery_location_id INTEGER NOT NULL,
        units_sold INTEGER NOT NULL,
        unit_price NUMERIC(10, 2) NOT NULL,
        CONSTRAINT fk_sales_staff
            FOREIGN KEY (sales_staff_id)
            REFERENCES dim_staff(staff_id),
        CONSTRAINT fk_sales_counterparty
            FOREIGN KEY (sales_counterparty_id)
            REFERENCES dim_counterparty(counterparty_id),
        CONSTRAINT fk_sales_design
            FOREIGN KEY (design_id)
            REFERENCES dim_design(design_id),
        CONSTRAINT fk_sales_currency
            FOREIGN KEY (currency_id)
            REFERENCES dim_currency(currency_id),
        CONSTRAINT fk_sales_location
            FOREIGN KEY (agreed_delivery_location_id)
            REFERENCES dim_location(location_id)
    );
    """,

    "fact_purchase_order": """
    CREATE TABLE IF NOT EXISTS fact_purchase_order (
        purchase_record_id BIGSERIAL PRIMARY KEY,
        purchase_order_id INTEGER NOT NULL,
        created_date DATE ,
        created_time TIME ,
        last_updated_date DATE ,
        last_updated_time TIME ,
        staff_id INTEGER NOT NULL,
        counterparty_id INTEGER NOT NULL,
        currency_id INTEGER NOT NULL,
        item_code TEXT NOT NULL,
        item_quantity INTEGER NOT NULL,
        item_unit_price NUMERIC(10,2) NOT NULL,
        agreed_delivery_date DATE NOT NULL,
        agreed_payment_date DATE NOT NULL,
        agreed_delivery_location_id INTEGER NOT NULL,
        CONSTRAINT fk_purchase_staff
            FOREIGN KEY (staff_id)
            REFERENCES dim_staff(staff_id),
        CONSTRAINT fk_purchase_counterparty
            FOREIGN KEY (counterparty_id)
            REFERENCES dim_counterparty(counterparty_id),
        CONSTRAINT fk_purchase_currency
            FOREIGN KEY (currency_id)
            REFERENCES dim_currency(currency_id),
        CONSTRAINT fk_purchase_location
            FOREIGN KEY (agreed_delivery_location_id)
            REFERENCES dim_location(location_id)
    );
    """,

    "fact_payment": """
    CREATE TABLE IF NOT EXISTS fact_payment (
        payment_id INTEGER PRIMARY KEY,
        transaction_id INTEGER NOT NULL,
        counterparty_id INTEGER NOT NULL,
        currency_id INTEGER NOT NULL,
        payment_type_id INTEGER NOT NULL,
        payment_date DATE NOT NULL,
        payment_amount NUMERIC(12,2) NOT NULL,
        paid BOOLEAN NOT NULL,
        CONSTRAINT fk_payment_counterparty
            FOREIGN KEY (counterparty_id)
            REFERENCES dim_counterparty(counterparty_id),
        CONSTRAINT fk_payment_currency
            FOREIGN KEY (currency_id)
            REFERENCES dim_currency(currency_id),
        CONSTRAINT fk_payment_type
            FOREIGN KEY (payment_type_id)
            REFERENCES dim_payment_type(payment_type_id)
    );
    """,
}
