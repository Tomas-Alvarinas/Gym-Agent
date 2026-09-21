"""Envío de mensajes salientes por Telegram (Bot API).

Único módulo que sabe hablar con Telegram -- scheduler.py nunca arma
requests HTTP directamente, solo llama a send_telegram_message().

send_telegram_message() nunca lanza por fallas de red o de la API:
devuelve False para que el llamador (scheduler.py) decida qué hacer
-- en particular, no marcar el reminder como disparado si el envío
no fue exitoso.
"""
import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

_API_URL = "https://api.telegram.org/bot{token}/sendMessage"


def send_telegram_message(text: str) -> bool:
    """Envía 'text' al chat configurado (TELEGRAM_CHAT_ID).

    Devuelve True únicamente si Telegram confirmó la entrega (HTTP 200
    y {"ok": true} en la respuesta). Cualquier otro caso (credenciales
    faltantes, error de red, timeout, respuesta no-ok) devuelve False.
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False

    url = _API_URL.format(token=TELEGRAM_BOT_TOKEN)
    try:
        response = requests.post(
            url,
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text},
            timeout=10,
        )
    except requests.RequestException:
        return False

    if response.status_code != 200:
        return False

    try:
        return bool(response.json().get("ok", False))
    except ValueError:
        return False
