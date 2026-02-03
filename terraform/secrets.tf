


data "aws_secretsmanager_secret" "totesys_creds" {
  name = "${var.project_name}/totesys/${var.environment}"
}


resource "aws_secretsmanager_secret" "dw_creds" {
  name                    = "${var.project_name}/dw/${var.environment}"
  description             = "Data warehouse RDS credentials"
  recovery_window_in_days = 0
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
  special = false
}