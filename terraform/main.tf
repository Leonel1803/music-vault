locals {
  name = "${var.project_name}-${var.environment}"
}

module "dynamodb" {
  source                        = "./modules/dynamodb"
  table_name                    = "${local.name}-data"
  enable_point_in_time_recovery = var.enable_point_in_time_recovery
}

module "cognito" {
  source        = "./modules/cognito"
  name          = local.name
  domain_prefix = var.cognito_domain_prefix
  callback_urls = [for origin in var.allowed_origins : "${origin}/"]
  logout_urls   = [for origin in var.allowed_origins : "${origin}/"]
}

module "lambda" {
  source             = "./modules/lambda"
  name               = local.name
  table_arn          = module.dynamodb.table_arn
  table_name         = module.dynamodb.table_name
  source_dir         = "${path.root}/../backend"
  log_retention_days = var.log_retention_days
}

module "api_gateway" {
  source              = "./modules/api_gateway"
  name                = local.name
  invoke_arns         = module.lambda.invoke_arns
  user_pool_issuer    = module.cognito.issuer
  user_pool_client_id = module.cognito.app_client_id
  allowed_origins     = var.allowed_origins
  log_retention_days  = var.log_retention_days
  enable_access_logs  = var.enable_api_access_logs
}

resource "aws_lambda_permission" "api" {
  for_each      = module.lambda.function_names
  statement_id  = "AllowApiGateway-${each.key}"
  action        = "lambda:InvokeFunction"
  function_name = each.value
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${module.api_gateway.execution_arn}/*/*"
}

module "hosting" {
  source = "./modules/hosting"
  name   = local.name
}

module "cloudwatch" {
  source        = "./modules/cloudwatch"
  name          = local.name
  lambda_names  = values(module.lambda.function_names)
  api_id        = module.api_gateway.api_id
  table_name    = module.dynamodb.table_name
  alarm_email   = var.alarm_email
  enable_alarms = var.enable_alarms
}
