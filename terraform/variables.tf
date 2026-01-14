variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "gamboge-etl"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-2"
}

# Totesys Database Credentials
variable "totesys_db_host" {
  description = "Totesys database host"
  type        = string
}

variable "totesys_db_name" {
  description = "Totesys database name"
  type        = string
  default     = "totesys"
}

variable "totesys_db_user" {
  description = "Totesys database username"
  type        = string
}

variable "totesys_db_password" {
  description = "Totesys database password"
  type        = string
  sensitive   = true
}

variable "totesys_db_port" {
  description = "Totesys database port"
  type        = number
  default     = 5432
}

# Alerting
variable "alert_email" {
  description = "Email for alerts"
  type        = string
}

# Lambda Configuration
variable "lambda_timeout" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 600
}

variable "lambda_memory_size" {
  description = "Lambda memory in MB"
  type        = number
  default     = 512
}

variable "lambda_runtime" {
  description = "Lambda runtime"
  type        = string
  default     = "python3.11"
}

# Schedule
variable "ingestion_schedule" {
  description = "EventBridge schedule expression"
  type        = string
  default     = "rate(15 minutes)"
}

# warehouse variables
variable "dw_db_username" {
  description = "Data warehouse database username"
  type        = string
  default     = "warehouse_admin"
}
variable "dw_db_password" {
  description = "Data warehouse database password"
  type        = string
  sensitive   = true
}
variable "rds_instance_class" {
  description = "RDS instance type"
  type        = string
  default     = "db.t3.micro"
}
variable "rds_allocated_storage" {
  description = "RDS storage in GB"
  type        = number
  default     = 20
}
variable "rds_backup_retention" {
  description = "RDS backup retention in days"
  type        = number
  default     = 7
}
variable "rds_engine_version" {
  description = "PostgreSQL engine version"
  type        = string
  default     = "14.17"
}

# variable "rds_multi_az" {
#   description = "Enable Multi-AZ deployment"
#   type        = bool
#   default     = false  # true for production
# }

# VPC Configuration Variables
variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24"]
}

variable "db_subnet_cidrs" {
  description = "CIDR blocks for database subnets"
  type        = list(string)
  default     = ["10.0.20.0/24", "10.0.21.0/24"]
}

variable "availability_zones" {
  description = "Availability zones to use"
  type        = list(string)
  default     = ["eu-west-2a", "eu-west-2b"]
}