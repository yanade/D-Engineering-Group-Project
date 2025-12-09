data "archive_file" "etl_lambda" {
  type = "zip"

  # etl_handler.py lives in ../lambda relative to terrafrom/
  source_file = "${path.module}/../lambda/etl_handler.py"

  # Terraform will create this zip file for you
  output_path      = "${path.module}/../lambda/etl_handler.zip"
  output_file_mode = "0666"
}
# THIS WILL HAVE TO CHANGE !! 

