"""Backend logic для заметок (минимальный каркас)."""

from apps.integrations.bpium.client import BpiumClient


class NotesService:
    def __init__(self, bpium_client: BpiumClient, user_context: dict):
        self.bpium_client = bpium_client
        self.user_context = user_context

    async def ingest_txt(self, document_payload: dict) -> None:
        self.bpium_client.save_note(
            user_context=self.user_context,
            source_type="txt",
            content_text=f"TXT placeholder: {document_payload.get('file_name', 'unknown.txt')}",
        )

    async def save_text_note(self, note_text: str) -> dict:
        telegram_user_id = self.user_context.get("telegram_user_id", "")
        # Обязательная повторная проверка пользователя через Bpium перед сохранением.
        verified_user = self.bpium_client.check_user(telegram_user_id=telegram_user_id)
        if not verified_user:
            raise ValueError("User is not active in Bpium")

        return self.bpium_client.save_text_note(
            telegram_user_id=telegram_user_id,
            text=note_text,
        )

    async def save_voice_note(self, voice_payload: dict) -> None:
        transcript = self.bpium_client.transcribe_voice(voice_payload=voice_payload)
        self.bpium_client.save_note(
            user_context=self.user_context,
            source_type="voice",
            content_text=transcript,
        )

    async def search_notes_text(self, query: str) -> list[dict]:
        return self.bpium_client.search_notes_text(
            user_context=self.user_context,
            query=query,
        )

    async def list_notes_stub(self) -> list[dict]:
        return self.bpium_client.list_notes(user_context=self.user_context)
