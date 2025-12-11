# resource "null_resource" "build_layer" {
#   triggers = {
#     # Rebuild when requirements.txt changes
#     requirements_hash = filemd5("${path.module}/../requirements.txt")
#     # Rebuild when build script changes
#     script_hash = filemd5("${path.module}/../scripts/build_layer.sh")
#   }

#   provisioner "local-exec" {
#     command = "bash ${path.module}/../scripts/build_layer.sh"
#   }
# }


resource "aws_lambda_layer_version" "dependencies" {
  # depends_on = [null_resource.build_layer]
  layer_name          = "${var.project_name}-dependencies"
  filename            = "${path.module}/../lambda_layer/lambda_layer.zip"
  # source_code_hash    = filebase64sha256("${path.module}/../lambda_layer.zip")
  compatible_runtimes = ["python3.12"]
  description = "Python dependencies for ingestion lambda"
}