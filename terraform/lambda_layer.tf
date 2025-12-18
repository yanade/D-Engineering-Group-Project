
# -------------------------------------------------
# LAMBDA LAYER FOR SHARED DEPENDENCIES
# -------------------------------------------------

# Create ZIP from the built layer directory
# data "archive_file" "dependencies_layer" {
#   type        = "zip"
#   source_dir  = "${path.module}/../lambda_layer"
#   output_path = "${path.module}/../dist/dependencies_layer.zip"
  
  # This depends on the build script being run first
  # depends_on = [null_resource.build_layer]
# }

# # Resource to trigger build script before Terraform runs
# resource "null_resource" "build_layer" {
#   triggers = {
#     # Rebuild when requirements.txt changes
#     requirements_hash = filemd5("${path.module}/../requirements.txt")
#     # Rebuild when build script changes
#     script_hash = filemd5("${path.module}/../scripts/build_layer.sh")
#   }
  
#   provisioner "local-exec" {
#     command = "chmod +x ${path.module}/../scripts/build_layer.sh && ${path.module}/../scripts/build_layer.sh"
#   }
# }
resource "aws_lambda_layer_version" "dependencies" {
  layer_name          = "${var.project_name}-dependencies"
  filename            = "${path.module}/../lambda_layer/lambda_layer.zip"
  compatible_runtimes = ["python3.12"]
  description = "Python dependencies for ingestion lambda"
}
# resource "aws_lambda_layer_version" "dependencies" {
#   layer_name          = "${var.project_name}-dependencies-${var.environment}"
#   description         = "Shared Python dependencies for ETL pipeline"
#   filename            = data.archive_file.dependencies_layer.output_path
#   source_code_hash    = data.archive_file.dependencies_layer.output_base64sha256
#   compatible_runtimes = [var.lambda_runtime]  # ["python3.11"]
  

  # depends_on = [
  #   # null_resource.build_layer,
  #   data.archive_file.dependencies_layer
  # ]
# }

