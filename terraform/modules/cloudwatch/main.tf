data "aws_region" "current" {}

locals {
  alarms_on = var.enable_alarms
  services  = ["catalog", "interactions", "library"]
}

resource "aws_sns_topic" "alarms" {
  count = local.alarms_on ? 1 : 0
  name  = "${var.name}-alarms"
}

resource "aws_sns_topic_subscription" "email" {
  count     = local.alarms_on && var.alarm_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alarms[0].arn
  protocol  = "email"
  endpoint  = var.alarm_email
}

resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  for_each            = local.alarms_on ? toset(var.lambda_names) : toset([])
  alarm_name          = "${each.key}-errors"
  namespace           = "AWS/Lambda"
  metric_name         = "Errors"
  dimensions          = { FunctionName = each.key }
  statistic           = "Sum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 1
  comparison_operator = "GreaterThanOrEqualToThreshold"
  treat_missing_data  = "notBreaching"
  alarm_actions       = [aws_sns_topic.alarms[0].arn]
}

# RNF-15: tablero único con Lambda, API Gateway, DynamoDB y métricas propias.
resource "aws_cloudwatch_dashboard" "this" {
  dashboard_name = "${var.name}-overview"
  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric", x = 0, y = 0, width = 12, height = 6
        properties = {
          title  = "Lambda: invocaciones y errores"
          region = data.aws_region.current.name
          stat   = "Sum"
          period = 300
          metrics = concat(
            [for fn in var.lambda_names : ["AWS/Lambda", "Invocations", "FunctionName", fn]],
            [for fn in var.lambda_names : ["AWS/Lambda", "Errors", "FunctionName", fn]]
          )
        }
      },
      {
        type = "metric", x = 12, y = 0, width = 12, height = 6
        properties = {
          title   = "Lambda: duración promedio (ms)"
          region  = data.aws_region.current.name
          stat    = "Average"
          period  = 300
          metrics = [for fn in var.lambda_names : ["AWS/Lambda", "Duration", "FunctionName", fn]]
        }
      },
      {
        type = "metric", x = 0, y = 6, width = 12, height = 6
        properties = {
          title  = "API Gateway: solicitudes y errores"
          region = data.aws_region.current.name
          stat   = "Sum"
          period = 300
          metrics = [
            ["AWS/ApiGateway", "Count", "ApiId", var.api_id],
            ["AWS/ApiGateway", "4xx", "ApiId", var.api_id],
            ["AWS/ApiGateway", "5xx", "ApiId", var.api_id]
          ]
        }
      },
      {
        type = "metric", x = 12, y = 6, width = 12, height = 6
        properties = {
          title  = "DynamoDB: capacidad consumida"
          region = data.aws_region.current.name
          stat   = "Sum"
          period = 300
          metrics = [
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", var.table_name],
            ["AWS/DynamoDB", "ConsumedWriteCapacityUnits", "TableName", var.table_name]
          ]
        }
      },
      {
        type = "metric", x = 0, y = 12, width = 12, height = 6
        properties = {
          title  = "MusicVault: solicitudes y errores 5xx"
          region = data.aws_region.current.name
          stat   = "Sum"
          period = 300
          metrics = concat(
            [for s in local.services : ["MusicVault", "Requests", "Service", s]],
            [for s in local.services : ["MusicVault", "ServerErrors", "Service", s]]
          )
        }
      },
      {
        type = "metric", x = 12, y = 12, width = 12, height = 6
        properties = {
          title  = "MusicVault: contribuciones y latencia"
          region = data.aws_region.current.name
          stat   = "Average"
          period = 300
          metrics = concat(
            [["MusicVault", "Contributions", "Service", "interactions", { stat = "Sum" }]],
            [for s in local.services : ["MusicVault", "LatencyMs", "Service", s]]
          )
        }
      }
    ]
  })
}

output "dashboard_name" {
  value = aws_cloudwatch_dashboard.this.dashboard_name
}
