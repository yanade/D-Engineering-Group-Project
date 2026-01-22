resource "aws_lambda_permission" "allow_s3_invoke_transform" {
  statement_id  = "AllowS3InvokeTransform"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.transform.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.landing_zone.arn
}


resource "aws_s3_bucket_notification" "landing_triggers_transform" {
  bucket = aws_s3_bucket.landing_zone.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.transform.arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".json"
  }

  depends_on = [aws_lambda_permission.allow_s3_invoke_transform]
}


resource "aws_lambda_permission" "allow_s3_invoke_loading" {
  statement_id  = "AllowS3InvokeLoading"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.loading.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.processed_zone.arn
}




resource "aws_s3_bucket_notification" "transform_triggers_loading" {
  bucket = aws_s3_bucket.processed_zone.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.loading.arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ".parquet"
    filter_prefix       = ""
  }

  depends_on = [aws_lambda_permission.allow_s3_invoke_loading]
}