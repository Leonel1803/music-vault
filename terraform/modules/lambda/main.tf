data "archive_file" "backend" {
  type        = "zip"
  source_dir  = var.source_dir
  excludes    = ["scripts/**", "tests/**", "requirements-dev.txt"]
  output_path = "${path.root}/.terraform/backend.zip"
}

# Una función por caso de uso. Cada una recibe solo las acciones de DynamoDB que necesita.
locals {
  functions = {
    catalog = {
      handler = "src.handler.catalog_lambda_handler"
      actions = ["dynamodb:GetItem", "dynamodb:Query"]
    }
    interactions = {
      handler = "src.handler.interactions_lambda_handler"
      actions = ["dynamodb:Query", "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:DeleteItem", "dynamodb:UpdateItem"]
    }
    library = {
      handler = "src.handler.library_lambda_handler"
      actions = ["dynamodb:Query", "dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:DeleteItem"]
    }
  }
}

resource "aws_iam_role" "lambda" {
  for_each = local.functions
  name     = "${var.name}-${each.key}-lambda"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_cloudwatch_log_group" "lambda" {
  for_each          = local.functions
  name              = "/aws/lambda/${var.name}-${each.key}"
  retention_in_days = var.log_retention_days
}

resource "aws_iam_role_policy" "lambda" {
  for_each = local.functions
  name     = "${var.name}-${each.key}-runtime"
  role     = aws_iam_role.lambda[each.key].id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = each.value.actions
        Resource = [var.table_arn, "${var.table_arn}/index/*"]
      },
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "${aws_cloudwatch_log_group.lambda[each.key].arn}:*"
      }
    ]
  })
}

resource "aws_lambda_function" "this" {
  for_each         = local.functions
  function_name    = "${var.name}-${each.key}"
  role             = aws_iam_role.lambda[each.key].arn
  handler          = each.value.handler
  runtime          = "python3.12"
  timeout          = 10
  memory_size      = 256
  filename         = data.archive_file.backend.output_path
  source_code_hash = data.archive_file.backend.output_base64sha256

  environment {
    variables = {
      TABLE_NAME = var.table_name
      LOG_LEVEL  = "INFO"
    }
  }

  depends_on = [aws_cloudwatch_log_group.lambda, aws_iam_role_policy.lambda]
}
