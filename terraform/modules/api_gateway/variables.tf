variable "name" {
  type = string
}

variable "invoke_arns" {
  description = "ARN de invocación por función (catalog, interactions, library)."
  type        = map(string)
}

variable "user_pool_issuer" {
  type = string
}

variable "user_pool_client_id" {
  type = string
}

variable "allowed_origins" {
  type = list(string)
}

variable "log_retention_days" {
  type = number
}

variable "enable_access_logs" {
  type = bool
}
