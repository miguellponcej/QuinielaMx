locals {
  ssh_public_key = file(pathexpand(var.ssh_public_key_path))
  server_name    = var.domain_name != "" ? var.domain_name : "_"
}

resource "digitalocean_ssh_key" "deploy" {
  name       = var.ssh_key_name
  public_key = local.ssh_public_key
}

resource "digitalocean_droplet" "app" {
  image    = var.ubuntu_image
  name     = var.droplet_name
  region   = var.region
  size     = var.droplet_size
  ssh_keys = [digitalocean_ssh_key.deploy.fingerprint]
  user_data = templatefile("${path.module}/cloud-init.yaml", {
    deploy_user      = var.deploy_user
    ssh_public_key   = local.ssh_public_key
    server_name      = local.server_name
    authorized_email = var.authorized_email
  })

  tags = ["quiniela-predictor", "private-app"]
}

resource "digitalocean_firewall" "app" {
  name        = "${var.droplet_name}-firewall"
  droplet_ids = [digitalocean_droplet.app.id]

  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "80"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "443"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "udp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "icmp"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}
