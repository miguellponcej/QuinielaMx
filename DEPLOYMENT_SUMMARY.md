# Despliegue QuinielaPredictor MX

Fecha: 2026-05-10
Proveedor cloud: DigitalOcean recomendado
Region: nyc3 propuesta
Nombre de VM: quiniela-predictor-mx
IP publica: PENDIENTE
Dominio: PENDIENTE
URL final: PENDIENTE
URL HTTP: PENDIENTE
URL HTTPS: PENDIENTE
Estado de HTTPS: PENDIENTE
Estado de la app: No desplegada; faltan credenciales cloud
Estado de autenticacion: Implementada en la app; requiere .env real con secretos
Usuario autorizado: Miguel Angel <miguellponcej@gmail.com>
Ruta del proyecto en VM: /opt/quiniela_predictor_mx

## Credencial faltante

Falta configurar `DIGITALOCEAN_TOKEN` en el entorno donde se ejecutara Terraform.

```bash
export DIGITALOCEAN_TOKEN="dop_v1_TU_TOKEN"
```

## Comandos finales

Crear VM:

```bash
infra/scripts/provision_vm.sh -var "region=nyc3" -var "droplet_name=quiniela-predictor-mx"
```

Desplegar app:

```bash
infra/scripts/deploy_app.sh quiniela@IP_PUBLICA
```

Activar HTTPS:

```bash
ssh quiniela@IP_PUBLICA
sudo /opt/quiniela_predictor_mx/infra/scripts/setup_ssl.sh DOMINIO_O_IP.sslip.io tu-correo@example.com
```

Obtener URL final:

```bash
ssh quiniela@IP_PUBLICA
/opt/quiniela_predictor_mx/infra/scripts/get_public_url.sh
```

Comando para reiniciar:

```bash
ssh quiniela@IP_PUBLICA '/opt/quiniela_predictor_mx/infra/scripts/restart_app.sh'
```

Comando para ver logs:

```bash
ssh quiniela@IP_PUBLICA 'cd /opt/quiniela_predictor_mx && docker compose logs -f --tail=100'
```

Comando para actualizar app:

```bash
infra/scripts/deploy_app.sh quiniela@IP_PUBLICA
```

Comando para detener app:

```bash
ssh quiniela@IP_PUBLICA 'cd /opt/quiniela_predictor_mx && docker compose down'
```
