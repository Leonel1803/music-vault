locals {
  # Cada ruta indica qué función la atiende y si exige JWT de Cognito.
  routes = {
    "GET /artists"                   = { target = "catalog", auth = false }
    "GET /artists/{artistId}"        = { target = "catalog", auth = false }
    "GET /artists/{artistId}/albums" = { target = "catalog", auth = false }
    "GET /albums"                    = { target = "catalog", auth = false }
    "GET /albums/{albumId}"          = { target = "catalog", auth = false }
    "GET /albums/{albumId}/songs"    = { target = "catalog", auth = false }
    "GET /songs"                     = { target = "catalog", auth = false }
    "GET /songs/{songId}"            = { target = "catalog", auth = false }
    "GET /songs/{songId}/reviews"    = { target = "catalog", auth = false }
    "GET /search"                    = { target = "catalog", auth = false }
    "GET /me/favorites"              = { target = "interactions", auth = true }
    "PUT /me/favorites/{songId}"     = { target = "interactions", auth = true }
    "DELETE /me/favorites/{songId}"  = { target = "interactions", auth = true }
    "GET /me/ratings/{songId}"       = { target = "interactions", auth = true }
    "PUT /me/ratings/{songId}"       = { target = "interactions", auth = true }
    "DELETE /me/ratings/{songId}"    = { target = "interactions", auth = true }
    "GET /me/reviews/{songId}"       = { target = "interactions", auth = true }
    "PUT /me/reviews/{songId}"       = { target = "interactions", auth = true }
    "DELETE /me/reviews/{songId}"    = { target = "interactions", auth = true }
    "GET /me/library"                = { target = "library", auth = true }
    "PUT /me/library/{songId}"       = { target = "library", auth = true }
    "DELETE /me/library/{songId}"    = { target = "library", auth = true }
  }
}

resource "aws_cloudwatch_log_group" "api" {
  count             = var.enable_access_logs ? 1 : 0
  name              = "/aws/apigateway/${var.name}"
  retention_in_days = var.log_retention_days
}

resource "aws_apigatewayv2_api" "this" {
  name          = "${var.name}-api"
  protocol_type = "HTTP"
  cors_configuration {
    allow_origins = var.allowed_origins
    allow_methods = ["GET", "PUT", "DELETE", "OPTIONS"]
    allow_headers = ["authorization", "content-type"]
    max_age       = 300
  }
}

resource "aws_apigatewayv2_authorizer" "jwt" {
  api_id           = aws_apigatewayv2_api.this.id
  name             = "${var.name}-cognito-jwt"
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  jwt_configuration {
    audience = [var.user_pool_client_id]
    issuer   = var.user_pool_issuer
  }
}

resource "aws_apigatewayv2_integration" "this" {
  for_each               = var.invoke_arns
  api_id                 = aws_apigatewayv2_api.this.id
  integration_type       = "AWS_PROXY"
  integration_uri        = each.value
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "this" {
  for_each           = local.routes
  api_id             = aws_apigatewayv2_api.this.id
  route_key          = each.key
  target             = "integrations/${aws_apigatewayv2_integration.this[each.value.target].id}"
  authorization_type = each.value.auth ? "JWT" : "NONE"
  authorizer_id      = each.value.auth ? aws_apigatewayv2_authorizer.jwt.id : null
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.this.id
  name        = "$default"
  auto_deploy = true
  dynamic "access_log_settings" {
    for_each = var.enable_access_logs ? [true] : []
    content {
      destination_arn = aws_cloudwatch_log_group.api[0].arn
      format = jsonencode({
        requestId      = "$context.requestId"
        requestTime    = "$context.requestTime"
        routeKey       = "$context.routeKey"
        status         = "$context.status"
        responseLength = "$context.responseLength"
        sourceIp       = "$context.identity.sourceIp"
      })
    }
  }
}
