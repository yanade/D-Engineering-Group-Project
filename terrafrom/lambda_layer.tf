resource "aws_lambda_layer_version" "dependencies" {
  layer_name          = "${var.project_name}-dependencies"
  filename            = "${path.module}/../lambda_layer.zip"
  source_code_hash    = filebase64sha256("${path.module}/../lambda_layer.zip")
  compatible_runtimes = ["python3.12"]
  description = "Python dependencies for ingestion lambda"
}