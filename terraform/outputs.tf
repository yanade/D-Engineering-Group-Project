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