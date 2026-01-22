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

# # data "aws_secretsmanager_secret_version" "totesys_creds_current" {
# #   secret_id = data.aws_secretsmanager_secret.totesys_creds.id
# # }
# locals {
#   totesys_secret = jsondecode(data.aws_secretsmanager_secret_version.totesys_creds_current.secret_string)
# }

# # Read the current value (JSON) of the secret
# data "aws_secretsmanager_secret_version" "totesys_creds_value" {
#   secret_id = data.aws_secretsmanager_secret.totesys_creds.id
# }

resource "aws_secretsmanager_secret" "dw_creds" {
  name        = "${var.project_name}/dw/${var.environment}"
  description = "Data warehouse RDS credentials"
  tags = {
    Stage       = "Week3-Loading"
    Environment = var.environment
    Database    = "warehouse"
  }
}
resource "aws_secretsmanager_secret_version" "dw_creds_v1" {
  secret_id = aws_secretsmanager_secret.dw_creds.id

  secret_string = jsonencode({
    host     = aws_db_instance.data_warehouse.address
    port     = aws_db_instance.data_warehouse.port
    database = aws_db_instance.data_warehouse.db_name
    user     = var.dw_db_username
    password = random_password.dw_password.result
  })
}

# data "aws_secretsmanager_secret_version" "dw_creds_value" {
#   secret_id = data.aws_secretsmanager_secret.dw_creds.id
# }

resource "random_password" "dw_password" {
  length  = 20
  special = true
}