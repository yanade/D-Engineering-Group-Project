# Schedule ingestion every 15 minutes
resource "aws_cloudwatch_event_rule" "ingestion_schedule" {
  name        = "${var.project_name}-ingestion-schedule"
  description = "Run ingestion every 15 minutes"
  
  schedule_expression = var.ingestion_schedule
  
  tags = {
    Stage = "Week1-Ingestion"
  }
}

resource "aws_cloudwatch_event_target" "ingestion_target" {
  rule      = aws_cloudwatch_event_rule.ingestion_schedule.name
  target_id = "ingestion-lambda"
  arn       = aws_lambda_function.ingestion.arn
}

# Allow EventBridge to invoke Lambda
resource "aws_lambda_permission" "eventbridge_ingestion" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingestion.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ingestion_schedule.arn
}