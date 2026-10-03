"""Integraciones de mensajería disparadas desde el ERP."""

import logging

import requests
from django.conf import settings
from requests.auth import HTTPBasicAuth


logger = logging.getLogger(__name__)


def enviar_factura_por_whatsapp(*, nombre_cliente, telefono, factura_url, numero_factura):
    """Envía los datos de una factura al webhook de n8n sin bloquear la venta."""
    webhook_url = settings.N8N_FACTURA_WHATSAPP_WEBHOOK_URL
    usuario = settings.N8N_FACTURA_WHATSAPP_USER
    password = settings.N8N_FACTURA_WHATSAPP_PASSWORD

    if not webhook_url:
        logger.warning("Webhook de WhatsApp no configurado; factura %s no enviada.", numero_factura)
        return False

    if not usuario or not password:
        logger.warning("Credenciales de WhatsApp no configuradas; factura %s no enviada.", numero_factura)
        return False

    payload = {
        "nombre_cliente": nombre_cliente,
        "telefono": telefono,
        "factura_url": factura_url,
        "numero_factura": str(numero_factura),
    }

    try:
        response = requests.post(
            webhook_url,
            json=payload,
            auth=HTTPBasicAuth(usuario, password),
            timeout=8,
        )
        response.raise_for_status()
        logger.info("Factura %s enviada al webhook de WhatsApp.", numero_factura)
        return True
    except requests.RequestException:
        logger.exception("No fue posible enviar la factura %s al webhook de WhatsApp.", numero_factura)
        return False
