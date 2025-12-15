# Store Totesys credentials in Secrets Manager
# resource "aws_secretsmanager_secret" "totesys_creds" {
#   name = "${var.project_name}/totesys/${var.environment}"
  
#   description = "Totesys database credentials for ingestion"
  
#   tags = {
#     Stage       = "Week1-Ingestion"
#     Environment = var.environment
#     Database    = "totesys"
#   }
# }

# resource "aws_secretsmanager_secret_version" "totesys_creds_value" {
#   secret_id = aws_secretsmanager_secret.totesys_creds.id
  
#   secret_string = jsonencode({
#     host     = var.totesys_db_host
#     port     = var.totesys_db_port
#     database = var.totesys_db_name
#     username = var.totesys_db_user
#     password = var.totesys_db_password
#   })
# }


data "aws_secretsmanager_secret" "totesys_creds" {
  name = "${var.project_name}/totesys/${var.environment}"
}
# Read the current value (JSON) of the secret
data "aws_secretsmanager_secret_version" "totesys_creds_value" {
  secret_id = data.aws_secretsmanager_secret.totesys_creds.id
}