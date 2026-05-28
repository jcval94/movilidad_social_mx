output "service_uri" {
  description = "URL HTTPS del servicio Cloud Run."
  value       = google_cloud_run_v2_service.api.uri
}

output "service_account_email" {
  description = "Cuenta de servicio usada por Cloud Run."
  value       = google_service_account.api.email
}
