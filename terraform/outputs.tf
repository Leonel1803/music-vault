output "api_base_url" {
  description = "URL base pública HTTPS de la API."
  value       = module.api_gateway.api_endpoint
}

output "frontend_bucket_name" {
  description = "Bucket privado para publicar frontend/dist."
  value       = module.hosting.bucket_name
}

output "cloudfront_domain_name" {
  description = "Dominio HTTPS de distribución CloudFront."
  value       = module.hosting.cloudfront_domain_name
}

output "cloudfront_distribution_id" {
  description = "ID necesario para invalidar la distribución tras publicar archivos."
  value       = module.hosting.distribution_id
}

output "cognito_user_pool_id" {
  description = "ID público del User Pool para configurar el frontend."
  value       = module.cognito.user_pool_id
}

output "cognito_app_client_id" {
  description = "ID público del App Client de Cognito."
  value       = module.cognito.app_client_id
}

output "cognito_domain" {
  description = "Dominio Hosted UI sin protocolo."
  value       = module.cognito.domain
}
