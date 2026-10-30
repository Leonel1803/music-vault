output "user_pool_id" {
  value = aws_cognito_user_pool.this.id
}
output "app_client_id" {
  value = aws_cognito_user_pool_client.this.id
}
output "issuer" {
  value = "https://cognito-idp.${data.aws_region.current.name}.amazonaws.com/${aws_cognito_user_pool.this.id}"
}
output "domain" {
  value = "${var.domain_prefix}.auth.${data.aws_region.current.name}.amazoncognito.com"
}

data "aws_region" "current" {}
