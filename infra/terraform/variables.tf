variable "digitalocean_token" {
  description = "DigitalOcean API token with read/write access."
  type        = string
  sensitive   = true
}

variable "ssh_public_key_path" {
  description = "Local SSH public key path to register in DigitalOcean."
  type        = string
  default     = "~/.ssh/id_ed25519.pub"
}

variable "ssh_key_name" {
  description = "Name for the DigitalOcean SSH key."
  type        = string
  default     = "quiniela-predictor-key"
}

variable "region" {
  description = "DigitalOcean region."
  type        = string
  default     = "nyc3"
}

variable "droplet_name" {
  description = "Name of the VM."
  type        = string
  default     = "quiniela-predictor-mx"
}

variable "droplet_size" {
  description = "Droplet size. s-2vcpu-2gb satisfies the minimum 2 vCPU/2 GB target."
  type        = string
  default     = "s-2vcpu-2gb"
}

variable "ubuntu_image" {
  description = "Ubuntu image slug."
  type        = string
  default     = "ubuntu-24-04-x64"
}

variable "deploy_user" {
  description = "Non-root deployment user."
  type        = string
  default     = "quiniela"
}

variable "domain_name" {
  description = "Optional domain or subdomain. Leave empty to use the VM IP."
  type        = string
  default     = ""
}

variable "authorized_email" {
  description = "Default authorized user email for the private app."
  type        = string
  default     = "miguellponcej@gmail.com"
}
