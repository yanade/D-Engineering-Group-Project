# 📊 Data Engineering Group Project Gamboge ETL Pipeline


## 📌 Project Overview

This project implements an end-to-end, event-driven data engineering pipeline on AWS. It ingests data from a transactional PostgreSQL database, transforms it into an analytics-ready star schema, and loads it into a data warehouse designed for BI and reporting use cases.

The project was built as a **group project** during the *Northcoders Data Engineering Bootcamp* and focuses on production-style patterns such as incremental ingestion, event-driven processing, infrastructure as code, and data quality considerations.

---

## 🏗️ Architecture

### Pipeline Stages

#### Ingestion

* Extract data from a source PostgreSQL database (Totesys)
* Perform incremental ingestion using timestamp-based logic
* Store raw data as JSON files in Amazon S3 (Landing Zone)
* Triggered on a schedule using Amazon EventBridge

#### Transformation

* Read raw JSON data from the S3 Landing Zone
* Transform data into dimension and fact tables (star schema)
* Write transformed data as Parquet files to Amazon S3 (Processed Zone)
* Automatically triggered by S3 object creation events

#### Loading

* Load transformed Parquet files into Amazon RDS (PostgreSQL)
* Dimension tables are upserted
* Fact tables are loaded incrementally using the watermark to avoid reprocessing
* Data warehouse is ready for analytics and BI tools

---

## ☁️ AWS Services Used

* AWS Lambda
* Amazon S3
* Amazon RDS (PostgreSQL)
* AWS Secrets Manager
* Amazon EventBridge
* Amazon CloudWatch
* Amazon VPC
* Terraform

---

## 🧰 Technologies & Versions

| Technology | Version / Notes  |
| ---------- | ---------------- |
| Python     | 3.11             |
| Terraform  | >= 1.0           |
| PostgreSQL | 14               |
| pg8000     | 1.31.5           |
| pandas     | AWS Lambda Layer |
| pyarrow    | AWS Lambda Layer |

---

## 📁 Project Structure

```
.
├── src/
│   ├── ingestion/
│   ├── transformation/
│   └── loading/
│
├── lambda_layer/
│   ├── python/
│   └── lambda_layer.zip
│
├── test/
│   ├── ingestion/
│   ├── transformation/
│   └── loading/
│
├── terraform/
│   ├── main.tf
│   ├── variables.tf
│   ├── vpc.tf
│   ├── s3.tf
│   ├── rds.tf
│   ├── iam.tf
│   ├── lambda_ingestion.tf
│   ├── lambda_transform.tf
│   ├── lambda_loading.tf
│   ├── cloudwatch.tf
│   ├── eventbridge.tf
│   ├── lambda_layer.tf
│   ├── outputs.tf
│   ├── terraform.tfvars
│   ├── secrets.tf
│   └── s3_triggers.tf
│
├── requirements.txt
├── pytest.ini
├── pyproject.toml
└── README.md
```

---

## ⚙️ Setup Instructions

### 1️⃣ Clone the repository

```bash
git clone <REPO_URL>
cd Data-Engineering-Group-Proj
```

### 2️⃣ Create and activate a virtual environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

### 3️⃣ Install Python dependencies (for local development & testing)

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4️⃣ Export required Terraform secrets

```bash
export TF_VAR_totesys_db_password="your_source_db_password"
export TF_VAR_dw_db_password="your_warehouse_db_password"
```

### 5️⃣ Initialise Terraform

```bash
cd terraform
terraform init
```

### 6️⃣ Review infrastructure changes

```bash
terraform plan
```

### 7️⃣ Deploy infrastructure

```bash
terraform apply
```

### 🧹 Teardown

```bash
terraform destroy
```

---

## ▶️ Running the Pipeline

### Ingestion

* Runs automatically every 15 minutes
* Can be manually triggered via the AWS Lambda console

### Transformation

* Automatically triggered when new JSON files arrive in the S3 Landing Zone

### Loading

* Automatically triggered when new Parquet files arrive in the S3 Processed Zone

---

## 🧪 Running Tests

### From the project root:

```bash
pytest
```

### Run specific test folders:

```bash
pytest test/ingestion
pytest test/transformation
pytest test/loading
```

---

## 🧹 Code Quality & Security Checks

```bash
black src test
flake8 src
bandit -r src
pip-audit
```

---

## 🧠 Design Decisions

* nfrastructure defined using Terraform to ensure repeatability and consistency
* Event-driven architecture using S3 triggers and EventBridge
* Incremental ingestion and loading using watermark-based logic
* AWS Secrets Manager used instead of hardcoded credentials
* Star schema chosen to support analytics-ready data modelling
* Lambda Layers used to manage dependencies efficiently

---

## ⚠️ Assumptions & Limitations

* The pipeline assumes reliable timestamp fields in source tables for incremental ingestion
* Error handling focuses on logging and observability rather than automatic retries
* The project is designed for learning and demonstration purposes rather than high-throughput production workloads

---
