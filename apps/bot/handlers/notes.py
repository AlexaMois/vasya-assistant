"""Заготовки handlers для TXT/text/voice заметок."""

from apps.backend.notes_service import NotesService


async def handle_txt(notes_service: NotesService, document_payload: dict) -> None:
    await notes_service.ingest_txt(document_payload=document_payload)


async def handle_text_note(notes_service: NotesService, note_text: str) -> dict:
    return await notes_service.save_text_note(note_text=note_text)


async def handle_voice_note(notes_service: NotesService, voice_payload: dict) -> None:
    await notes_service.save_voice_note(voice_payload=voice_payload)
