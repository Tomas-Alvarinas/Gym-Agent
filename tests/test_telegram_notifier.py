"""Pruebas de send_telegram_message, sin red real.

requests.post se mockea siempre -- ningún test de este archivo hace una
llamada HTTP real ni requiere credenciales válidas de Telegram.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest


def _patched_credentials():
    return patch("telegram_notifier.TELEGRAM_BOT_TOKEN", "test-token"), patch(
        "telegram_notifier.TELEGRAM_CHAT_ID", "12345"
    )


def test_send_telegram_message_success():
    from telegram_notifier import send_telegram_message

    fake_response = MagicMock(status_code=200)
    fake_response.json.return_value = {"ok": True}

    token_patch, chat_patch = _patched_credentials()
    with token_patch, chat_patch, patch(
        "telegram_notifier.requests.post", return_value=fake_response
    ) as mock_post:
        result = send_telegram_message("Recordatorio: tomar creatina")

    assert result is True
    args, kwargs = mock_post.call_args
    assert "test-token" in args[0]
    assert kwargs["json"] == {"chat_id": "12345", "text": "Recordatorio: tomar creatina"}


def test_send_telegram_message_http_error():
    from telegram_notifier import send_telegram_message

    fake_response = MagicMock(status_code=401)

    token_patch, chat_patch = _patched_credentials()
    with token_patch, chat_patch, patch(
        "telegram_notifier.requests.post", return_value=fake_response
    ):
        result = send_telegram_message("Recordatorio: tomar creatina")

    assert result is False


def test_send_telegram_message_ok_false_in_response():
    from telegram_notifier import send_telegram_message

    fake_response = MagicMock(status_code=200)
    fake_response.json.return_value = {"ok": False, "description": "chat not found"}

    token_patch, chat_patch = _patched_credentials()
    with token_patch, chat_patch, patch(
        "telegram_notifier.requests.post", return_value=fake_response
    ):
        result = send_telegram_message("Recordatorio: tomar creatina")

    assert result is False


def test_send_telegram_message_network_exception():
    import requests

    from telegram_notifier import send_telegram_message

    token_patch, chat_patch = _patched_credentials()
    with token_patch, chat_patch, patch(
        "telegram_notifier.requests.post", side_effect=requests.ConnectionError("no network")
    ):
        result = send_telegram_message("Recordatorio: tomar creatina")

    assert result is False


def test_send_telegram_message_missing_credentials_does_not_call_requests():
    from telegram_notifier import send_telegram_message

    with patch("telegram_notifier.TELEGRAM_BOT_TOKEN", None), patch(
        "telegram_notifier.TELEGRAM_CHAT_ID", None
    ), patch("telegram_notifier.requests.post") as mock_post:
        result = send_telegram_message("Recordatorio: tomar creatina")

    assert result is False
    mock_post.assert_not_called()


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
