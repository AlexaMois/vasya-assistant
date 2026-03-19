"""Заготовка handler для простого поиска заметок по тексту."""

from apps.backend.notes_service import NotesService


async def handle_search_note(notes_service: NotesService, query: str) -> None:
    await notes_service.search_notes_text(query=query)
