output "landing_zone_bucket" {
  description = "Name of the landing zone bucket"
  value       = aws_s3_bucket.landing_zone.bucket
}

output "ingestion_lambda_name" {
  description = "Name of the ingestion Lambda function"
  value       = aws_lambda_function.ingestion.function_name
}

output "lambda_layer_arn" {
  description = "ARN of the Lambda layer"
  value       = aws_lambda_layer_version.dependencies.arn
}

output "ingestion_schedule_arn" {
  description = "ARN of the EventBridge schedule"
  value       = aws_cloudwatch_event_rule.ingestion_schedule.arn
}

output "alert_topic_arn" {
  description = "ARN of the SNS alert topic"
  value       = aws_sns_topic.alerts.arn
}

output "cloudwatch_log_group" {
  description = "CloudWatch log group for Lambda"
  value       = aws_cloudwatch_log_group.ingestion_logs.name
}

output "secrets_manager_secret" {
  description = "Name of the Secrets Manager secret"
  value       = data.aws_secretsmanager_secret.totesys_creds.name
  sensitive   = true
}

output "lambda_iam_role" {
  description = "IAM role for Lambda functions"
  value       = aws_iam_role.lambda_exec.arn
}

output "data_warehouse_endpoint" {
  description = "RDS endpoint for data warehouse"
  value       = aws_db_instance.data_warehouse.address
  sensitive   = false
}

output "data_warehouse_port" {
  description = "RDS port for data warehouse"
  value       = aws_db_instance.data_warehouse.port
}

output "data_warehouse_db_name" {
  description = "RDS database name"
  value       = aws_db_instance.data_warehouse.db_name
}

output "load_lambda_name" {
  description = "Name of the load Lambda function"
  value       = aws_lambda_function.loading.function_name
}

output "dw_secret_arn" {
  description = "ARN of the data warehouse secret"
  value       = aws_secretsmanager_secret.dw_creds.arn
  sensitive   = true
}

# output "vpc_id" {
#   description = "VPC ID used for deployment"
#   value       = data.aws_vpc.default.id
#}

output "lambda_security_group_id" {
  description = "Security group ID for Lambda functions"
  value       = aws_security_group.lambda_sg.id
}

# VPC Outputs
output "vpc_id" {
  description = "ID of the ETL VPC"
  value       = aws_vpc.etl_vpc.id
}

output "private_subnet_ids" {
  description = "IDs of private subnets"
  value       = [aws_subnet.private_a.id, aws_subnet.private_b.id]
}

output "db_subnet_ids" {
  description = "IDs of database subnets"
  value       = [aws_subnet.db_a.id, aws_subnet.db_b.id]
}

output "vpc_endpoint_s3_id" {
  description = "ID of S3 VPC endpoint"
  value       = aws_vpc_endpoint.s3.id
}