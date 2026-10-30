variable "project_name" {
  type        = string
  description = "Nombre corto del proyecto, usado en nombres de recursos."
  default     = "music-vault"
}

variable "environment" {
  type        = string
  description = "Ambiente aislado: dev, test o prod."
  default     = "dev"
}

variable "aws_region" {
  type        = string
  description = "Región principal de AWS."
  default     = "us-east-2"
}

variable "cognito_domain_prefix" {
  type        = string
  description = "Prefijo de dominio Hosted UI globalmente único para Cognito."
  validation {
    condition     = length(var.cognito_domain_prefix) >= 1 && length(var.cognito_domain_prefix) <= 63 && can(regex("^[a-z0-9]([a-z0-9-]*[a-z0-9])?$", var.cognito_domain_prefix))
    error_message = "El prefijo de Cognito debe contener de 1 a 63 letras minúsculas, números o guiones."
  }
}

variable "allowed_origins" {
  type        = list(string)
  description = "Orígenes exactos permitidos por CORS y Cognito."
  default     = ["http://localhost:5173"]
}

variable "enable_point_in_time_recovery" {
  type        = bool
  description = "Habilita recuperación a un punto en el tiempo de DynamoDB."
  default     = false
}

variable "log_retention_days" {
  type        = number
  description = "Retención de grupos de logs CloudWatch."
  default     = 7
  validation {
    condition     = contains([1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1827, 3653], var.log_retention_days)
    error_message = "Usa un periodo de retención de CloudWatch soportado por AWS."
  }
}

variable "enable_api_access_logs" {
  type        = bool
  description = "Habilita logs de acceso de API Gateway; generan cargos por ingesta."
  default     = false
}

variable "enable_alarms" {
  type        = bool
  description = "Habilita alarmas CloudWatch para Lambdas; desactivado por defecto en el proyecto escolar."
  default     = false
}

variable "alarm_email" {
  type        = string
  description = "Correo opcional para alarmas; requiere enable_alarms=true."
  default     = ""
}
