
# -------------------------------------------------
# LAMBDA LAYER FOR SHARED DEPENDENCIES
# -------------------------------------------------


resource "aws_lambda_layer_version" "dependencies" {
  layer_name          = "${var.project_name}-dependencies"
  filename            = "${path.module}/../dist/dependencies_layer.zip"
  compatible_runtimes = ["python3.11"]
  description         = "Python dependencies for ingestion lambda"
}
