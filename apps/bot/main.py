"""Точка входа Telegram layer (webhook)."""

from fastapi import FastAPI, Request

from apps.bot.handlers.dispatcher import dispatch_update
from apps.integrations.bpium.client import BpiumClient

app = FastAPI(title="vasya-assistant MVP")
bpium_client = BpiumClient()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request) -> dict:
    """Минимальный webhook endpoint для Telegram update."""
    update = await request.json()
    return await dispatch_update(update=update, bpium_client=bpium_client)
