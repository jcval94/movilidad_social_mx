variable "project_id" {
  description = "ID del proyecto de Google Cloud."
  type        = string
}

variable "region" {
  description = "Región de Cloud Run."
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "Nombre del servicio Cloud Run."
  type        = string
  default     = "movilidad-social-api"
}

variable "image" {
  description = "URI de la imagen Docker publicada en Artifact Registry."
  type        = string
}

variable "allow_unauthenticated" {
  description = "Permite invocación pública si es true. Para producción privada, usar false."
  type        = bool
  default     = false
}

variable "environment" {
  description = "Ambiente lógico expuesto a la API."
  type        = string
  default     = "prod"
}
