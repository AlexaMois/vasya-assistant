"""Обработчик /start."""

from apps.bot.keyboards.main_menu import build_main_menu


async def handle_start(telegram_user_id: str) -> dict:
    """Минимальная точка для приветствия и меню.

    В реальной реализации здесь будет вызов Telegram API sendMessage.
    """
    return {
        "telegram_user_id": telegram_user_id,
        "text": "Привет! Это каркас MVP vasya-assistant.",
        "reply_markup": build_main_menu(),
    }
