
# VPC endpoint for S3 ( so lambda can access S3 without internet)
resource "aws_vpc_endpoint" "s3" {
    vpc_id       = data.aws_vpc.default.id
    service_name = "com.amazonaws.${var.aws_region}.s3"
    vpc_endpoint_type = "Gateway"
    route_table_ids = [data.aws_vpc.default.main_route_table_id]
    tags = {
        Name  = "${var.project_name}-s3-endpoint"
        Stage = "Week3-Loading"
    }
}
# VPC endpoint for secret manager
resource "aws_vpc_endpoint" "secretsmnager" {
    vpc_id              = data.aws_vpc.default.id
    service_name        = "com.amazonaws.${var.aws_region}.secretsmanager"
    vpc_endpoint_type   = "Interface"
    security_group_ids  = [aws_security_group.endpoints_sg.id]
    subnet_ids          = slice(data.aws_subnets.default.ids,0,2)
    private_dns_enabled = true
    tags = {
      Name  = "${var.project_name}-secretsmanager-endpoint"
      Stage = "Week3-Loading"
  }
}
# VPC endpoint for cloudwatch logs
resource "aws_vpc_endpoint" "cloudwatch_logs" {
    vpc_id              = data.aws_vpc.default.id
    service_name        = "com.amazonaws.${var.aws_region}.logs"
    vpc_endpoint_type   = "Interface"
    security_group_ids  = [aws_security_group.endpoints_sg.id]
    subnet_ids          = slice(data.aws_subnets.default.ids,0,2)
    private_dns_enabled = true
    tags = {
      Name  = "${var.project_name}-logs-endpoint"
      Stage = "Week3-Loading"
  }
}