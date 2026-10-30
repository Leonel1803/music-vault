output "function_names" {
  description = "Nombre de cada función por caso de uso."
  value       = { for key, fn in aws_lambda_function.this : key => fn.function_name }
}

output "invoke_arns" {
  description = "ARN de invocación de cada función, para API Gateway."
  value       = { for key, fn in aws_lambda_function.this : key => fn.invoke_arn }
}
