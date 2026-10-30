variable "name" {
  type = string
}

variable "lambda_names" {
  type = list(string)
}

variable "api_id" {
  type = string
}

variable "table_name" {
  type = string
}

variable "alarm_email" {
  type    = string
  default = ""
}

variable "enable_alarms" {
  type    = bool
  default = false
}
