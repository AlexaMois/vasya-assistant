"""Маршрутизация входящих Telegram update в минимальные handlers."""

from apps.backend.notes_service import NotesService
from apps.backend.summary_service import SummaryService
from apps.bot.handlers.start import handle_start
from apps.bot.handlers.notes import handle_txt, handle_text_note, handle_voice_note
from apps.bot.handlers.search import handle_search_note
from apps.integrations.bpium.client import BpiumAPIError, BpiumClient

NOTES_MODE = "notes"


async def dispatch_update(update: dict, bpium_client: BpiumClient) -> dict:
    message = update.get("message") or {}
    callback_query = update.get("callback_query") or {}

    from_user = message.get("from") or callback_query.get("from") or {}
    telegram_user_id = str(from_user.get("id", ""))
    if not telegram_user_id:
        return {"status": "ignored", "reason": "no_user"}

    # 1) Проверка пользователя в Bpium
    user_context = bpium_client.check_user(telegram_user_id=telegram_user_id)
    if not user_context:
        return {"status": "rejected", "reason": "user_not_found"}

    notes_service = NotesService(bpium_client=bpium_client, user_context=user_context)
    summary_service = SummaryService(bpium_client=bpium_client, user_context=user_context)

    text = (message.get("text") or "").strip()
    document = message.get("document") or {}
    voice = message.get("voice") or {}
    callback_data = (callback_query.get("data") or "").strip()

    if text == "/start":
        start_response = await handle_start(telegram_user_id=telegram_user_id)
        return {"status": "ok", "reply": start_response}

    if callback_data == "daily_summary":
        await summary_service.create_daily_summary()
        return {"status": "ok", "reply": {"text": "Summary дня собран."}}

    if callback_data == "notes":
        bpium_client.set_user_mode(telegram_user_id=telegram_user_id, mode=NOTES_MODE)
        return {
            "status": "ok",
            "reply": {
                "text": "Режим заметок включён. Отправьте следующее текстовое сообщение как заметку.",
            },
        }

    if callback_data == "find_note":
        await handle_search_note(notes_service=notes_service, query="")
        return {"status": "ok", "reply": {"text": "Введите запрос для поиска заметки."}}

    if voice:
        await handle_voice_note(notes_service=notes_service, voice_payload=voice)
        return {"status": "ok", "reply": {"text": "Голосовая заметка принята."}}

    if document and document.get("file_name", "").lower().endswith(".txt"):
        await handle_txt(notes_service=notes_service, document_payload=document)
        return {"status": "ok", "reply": {"text": "TXT принят."}}

    # Рабочий MVP-поток: сохраняем только если пользователь заранее включил режим "Заметки".
    if text and not text.startswith("/"):
        if bpium_client.get_user_mode(telegram_user_id=telegram_user_id) == NOTES_MODE:
            try:
                saved_note = await handle_text_note(notes_service=notes_service, note_text=text)
            except (BpiumAPIError, ValueError) as exc:
                return {
                    "status": "error",
                    "reply": {
                        "text": f"Не удалось сохранить заметку: {exc}",
                    },
                }

            bpium_client.clear_user_mode(telegram_user_id=telegram_user_id)
            return {
                "status": "ok",
                "reply": {
                    "text": f"Заметка сохранена\n\n{saved_note['text']}",
                },
            }
        return {"status": "ignored", "reason": "notes_mode_not_enabled"}

    return {"status": "ignored", "reason": "unsupported_event"}
