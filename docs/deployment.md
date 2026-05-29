# Guia rapida de despliegue

## Checklist antes de produccion

- Cambiar `APP_SECRET`.
- Cambiar `ADMIN_PASSWORD`.
- Usar PostgreSQL administrado.
- Activar Stripe live mode solo despues de probar test mode.
- Configurar webhook `checkout.session.completed`.
- Configurar dominio verificado en Resend.
- Confirmar que `NEXT_PUBLIC_APP_URL` coincide con el dominio final.
- Revisar textos comerciales para evitar promesas de rentabilidad garantizada.
- Verificar politica fiscal, terminos, reembolsos y soporte del vendedor.

## Seguridad

- No pedir seed phrases ni private keys.
- No guardar datos de tarjeta.
- No exponer variables `.env`.
- Proteger endpoints administrativos con sesion.
- Rotar credenciales si sospechas fuga.
- Revisar logs de auditoria para cambios de productos y generacion.

## Operacion

- Exporta ventas desde `/api/reports/sales.csv`.
- Revisa pagos pendientes en Stripe Dashboard.
- Usa la wallet BTC solo como referencia publica o destino manual.
- No automatices retiros ni conversiones sin confirmacion humana.
