# 📊 Gamboge ETL Pipeline

## Overview

This project implements an **end-to-end ETL (Extract, Transform, Load) data pipeline** using Python, AWS, and Terraform.

The pipeline:
- Extracts data from a source PostgreSQL database
- Stores raw data in Amazon S3
- Transforms the data into analytics-ready tables
- Loads the results into an AWS RDS PostgreSQL data warehouse

The solution is **serverless**, **event-driven**, and designed using **industry-standard data engineering practices**.

---

## 🏗️ Architecture

### Pipeline Stages

**Week 1 – Ingestion**
- Extract data from source PostgreSQL (Totesys)
- Incremental ingestion using timestamps
- Store raw JSON files in S3 (Landing Zone)
- Triggered on a schedule using EventBridge

**Week 2 – Transformation**
- Read raw data from S3
- Transform data into dimension and fact tables (star schema)
- Write Parquet files to S3 (Processed Zone)
- Triggered automatically by S3 events

**Week 3 – Loading**
- Load transformed Parquet files into RDS PostgreSQL
- Dimensions are upserted
- Fact tables are appended
- Warehouse ready for analytics and BI tools

---

## ☁️ AWS Services Used

- AWS Lambda
- Amazon S3
- Amazon RDS (PostgreSQL)
- AWS Secrets Manager
- Amazon EventBridge
- Amazon CloudWatch
- Amazon VPC
- Terraform

---

## 🧰 Technologies & Versions

| Technology | Version |
|-----------|--------|
| Python | 3.11 |
| Terraform | >= 1.0 |
| PostgreSQL | 14 |
| pg8000 | 1.31.5 |
| pandas | AWS Lambda Layer |
| pyarrow | AWS Lambda Layer |

---

## 📁 Project Structure

.
├── src/
│ ├── ingestion/
│ ├── transformation/
│ ├── loading/
|
├── lambda_layer/
│ ├── python/
│ ├── lambda_layer.zip
│ 
|
├── test/
│ ├── ingestion/
│ ├── transformation/
| |── loading/
│
├── terraform/
│ ├── main.tf
│ ├── variables.tf
│ ├── vpc.tf
│ ├── s3.tf
│ ├── rds.tf
│ ├── iam.tf
│ ├── lambda_ingestion.tf
│ ├── lambda_transform.tf
│ ├── lambda_loading.tf
│ ├── cloudwatch.tf
│ ├── eventbridge.tf
│ ├── lambda_layer.tf
│ ├── outputs.tf
│ ├── terraform.tfvars
│ ├── secrets.tf
│ ├── s3_triggers.tf
│ 
│
├── requirements.txt
├── pytest.ini
├── pyproject.toml
└── README.md



---

## ⚙️ Setup Instructions

### 1️⃣ Clone the repository

```bash
git clone <REPO_URL>
cd Data-Engineering-Group-Proj


### 2️⃣ Create and activate a virtual environment

python3.11 -m venv .venv
source .venv/bin/activate

### 3️⃣ Install Python dependencies (for local development & testing)

pip install --upgrade pip
pip install -r requirements.txt

### 4️⃣ Export required Terraform secrets

export TF_VAR_totesys_db_password="your_source_db_password"
export TF_VAR_dw_db_password="your_warehouse_db_password"


### 5️⃣ Initialise Terraform

cd terraform
terraform init

### 6️⃣ Review infrastructure changes

terraform plan


### 7️⃣ Deploy infrastructure

terraform apply

### 🧹 Teardown

terraform destroy




## ▶️ Running the Pipeline

Ingestion

- Runs automatically every 15 minutes

- Can be manually triggered via AWS Lambda console

Transformation

- Automatically triggered when new JSON files arrive in the landing S3 bucket

Loading

- Automatically triggered when new Parquet files arrive in the processed S3 bucket


## 🧪 Running Tests

### From the project root:

pytest

### Run specific test folders:

pytest test/ingestion
pytest test/transformation



## 🧹 Code Quality & Security Checks

black src test
flake8 src
bandit -r src
pip-audit


## 🧠 Design Decisions

- Infrastructure defined using Terraform for repeatability

- Event-driven architecture using S3 triggers

- Secrets Manager used instead of hardcoded credentials

- Star schema for analytics-ready warehouse

- pg8000 used for Lambda-safe PostgreSQL connections

- AWS-managed Lambda Layers used to reduce deployment size








