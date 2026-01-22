# SNS Topic for alerts
resource "aws_sns_topic" "alerts" {
  name = "${var.project_name}-alerts-${var.environment}"

  tags = {
    Stage = "Week1-Ingestion"
  }
}

resource "aws_sns_topic_subscription" "email_alerts" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# Alarm for Lambda errors
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${var.project_name}-lambda-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300 # 5 minutes
  statistic           = "Sum"
  threshold           = 1 # Alert on ANY error

  dimensions = {
    FunctionName = aws_lambda_function.ingestion.function_name
  }

  alarm_description = "Ingestion Lambda has errors"
  alarm_actions     = [aws_sns_topic.alerts.arn]

  tags = {
    Stage = "Week1-Ingestion"
  }
}

# Alarm for Lambda timeout
resource "aws_cloudwatch_metric_alarm" "lambda_timeout" {
  alarm_name          = "${var.project_name}-lambda-timeout"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Maximum"
  threshold           = 250000 # Alert if >250 seconds (almost timeout)

  dimensions = {
    FunctionName = aws_lambda_function.ingestion.function_name
  }

  alarm_description = "Ingestion Lambda is timing out"
  alarm_actions     = [aws_sns_topic.alerts.arn]

  tags = {
    Stage = "Week1-Ingestion"
  }
}

#--------------------------------
# PROCESSED ZONE
#--------------------------------


resource "aws_cloudwatch_metric_alarm" "transform_lambda_errors" {
  alarm_name          = "${var.project_name}-transform-lambda-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300 # 5 minutes
  statistic           = "Sum"
  threshold           = 1 # Alert on ANY error

  dimensions = {
    FunctionName = aws_lambda_function.transform.function_name
  }

  alarm_description = "Transform Lambda has errors"
  alarm_actions     = [aws_sns_topic.alerts.arn]

  tags = {
    Stage = "Week2-Transform"
  }
}

resource "aws_cloudwatch_metric_alarm" "transform_lambda_timeout" {
  alarm_name          = "${var.project_name}-transform-lambda-timeout"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Maximum"
  threshold           = 250000 # Alert if >250 seconds (almost timeout)

  dimensions = {
    FunctionName = aws_lambda_function.transform.function_name
  }

  alarm_description = "Transform Lambda is timing out"
  alarm_actions     = [aws_sns_topic.alerts.arn]


  tags = {
    Stage = "Week2-Transform"
  }
}





resource "aws_cloudwatch_metric_alarm" "loading_lambda_errors" {
  alarm_name          = "${var.project_name}-loading-lambda-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300 # 5 minutes
  statistic           = "Sum"
  threshold           = 1 # Alert on ANY error

  dimensions = {
    FunctionName = aws_lambda_function.loading.function_name
  }

  alarm_description = "Loading Lambda has errors"
  alarm_actions     = [aws_sns_topic.alerts.arn]

  tags = {
    Stage = "Week3-Loading"
  }
}

resource "aws_cloudwatch_metric_alarm" "loading_lambda_timeout" {
  alarm_name          = "${var.project_name}-loading-lambda-timeout"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Maximum"
  threshold           = 250000 # Alert if >250 seconds (almost timeout)

  dimensions = {
    FunctionName = aws_lambda_function.loading.function_name
  }

  alarm_description = "Loading Lambda is timing out"
  alarm_actions     = [aws_sns_topic.alerts.arn]


  tags = {
    Stage = "Week3-Loading"
  }
}