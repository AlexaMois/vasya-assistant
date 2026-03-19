"""Backend logic для summary дня (минимальный каркас)."""

from apps.integrations.bpium.client import BpiumClient


class SummaryService:
    def __init__(self, bpium_client: BpiumClient, user_context: dict):
        self.bpium_client = bpium_client
        self.user_context = user_context

    async def create_daily_summary(self) -> dict:
        notes = self.bpium_client.list_notes(user_context=self.user_context)
        summary_text = self._build_simple_summary(notes=notes)
        return self.bpium_client.save_daily_summary(
            user_context=self.user_context,
            summary_text=summary_text,
        )

    def _build_simple_summary(self, notes: list[dict]) -> str:
        if not notes:
            return "За день заметок пока нет."
        preview = [n.get("content_text", "")[:80] for n in notes[:5]]
        return "Summary дня:\n- " + "\n- ".join(preview)
