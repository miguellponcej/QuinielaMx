output "vm_public_ip" {
  value       = digitalocean_droplet.app.ipv4_address
  description = "Public IPv4 address of the VM."
}

output "app_http_url" {
  value       = var.domain_name != "" ? "http://${var.domain_name}" : "http://${digitalocean_droplet.app.ipv4_address}"
  description = "HTTP URL for first access before HTTPS."
}

output "app_https_url" {
  value       = var.domain_name != "" ? "https://${var.domain_name}" : "https://${digitalocean_droplet.app.ipv4_address}.sslip.io"
  description = "HTTPS URL after DNS/sslip.io and Certbot are configured."
}

output "ssh_command" {
  value       = "ssh ${var.deploy_user}@${digitalocean_droplet.app.ipv4_address}"
  description = "SSH command for the non-root deploy user."
}
