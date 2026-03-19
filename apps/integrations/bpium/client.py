"""Bpium client: реальная интеграция с каталогами пользователей и заметок."""

import os
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

KRASNOYARSK_TZ = ZoneInfo("Asia/Krasnoyarsk")


class BpiumAPIError(RuntimeError):
    """Ошибка при обращении к Bpium API."""


class BpiumClient:
    """Интеграция с Bpium API для MVP-потока текстовых заметок."""

    def __init__(self) -> None:
        self.base_url = self._read_required_env("BPIUM_BASE_URL").rstrip("/")
        self.login = self._read_required_env("BPIUM_LOGIN")
        self.password = self._read_required_env("BPIUM_PASSWORD")

        self.users_catalog_id = self._read_required_int_env("BPIUM_USERS_CATALOG_ID")
        self.notes_catalog_id = self._read_required_int_env("BPIUM_NOTES_CATALOG_ID")
        self.companies_catalog_id = self._read_required_int_env("BPIUM_COMPANIES_CATALOG_ID")
        self.command_log_catalog_id = self._read_required_int_env("BPIUM_COMMAND_LOG_CATALOG_ID")

        self.request_timeout_sec = float(os.getenv("BPIUM_TIMEOUT_SEC", "15"))
        self._session = httpx.Client(base_url=self.base_url, timeout=self.request_timeout_sec)
        self._is_authenticated = False

        self._user_modes: dict[str, str] = {}
        self._summaries: list[dict] = []

    def check_user(self, telegram_user_id: str) -> dict | None:
        """Ищет пользователя в каталоге users по полю `Telegram ID` и проверяет статус."""
        record = self._find_user_by_telegram_id(telegram_user_id=telegram_user_id)
        if not record:
            return None

        status = (self._extract_field(record, "Статус") or "").strip().lower()
        if status and status not in {"активен", "active"}:
            return None

        company_ref = self._extract_field(record, "Компания")
        company_id = self._extract_linked_id(company_ref)
        if not company_id:
            return None

        return {
            "telegram_user_id": telegram_user_id,
            "user_id": str(record.get("id")),
            "tenant_id": str(company_id),
            "status": status or "active",
        }

    def set_user_mode(self, telegram_user_id: str, mode: str) -> None:
        self._user_modes[telegram_user_id] = mode

    def get_user_mode(self, telegram_user_id: str) -> str | None:
        return self._user_modes.get(telegram_user_id)

    def clear_user_mode(self, telegram_user_id: str) -> None:
        self._user_modes.pop(telegram_user_id, None)

    def save_text_note(self, telegram_user_id: str, text: str) -> dict:
        """Создаёт запись заметки в каталоге notes с реальными полями Bpium."""
        user_context = self.check_user(telegram_user_id=telegram_user_id)
        if not user_context:
            raise BpiumAPIError("Пользователь не найден или не активен в Bpium")

        now = datetime.now(KRASNOYARSK_TZ)
        created_at = now.strftime("%Y-%m-%d %H:%M:%S")

        payload = {
            "values": {
                "Заголовок": text[:80] if text else "Заметка из Telegram",
                "Текст заметки": text,
                "Автор": {"id": int(user_context["user_id"]), "catalog_id": self.users_catalog_id},
                "Компания": {"id": int(user_context["tenant_id"]), "catalog_id": self.companies_catalog_id},
                "Тип источника": "текст",
                "Дата создания": created_at,
                "Статус заметки": "активна",
                "Telegram message_id": None,
                "Исходный текст распознавания": text,
            }
        }

        self._request(
            method="POST",
            path=f"/catalogs/{self.notes_catalog_id}/records",
            json=payload,
        )

        return payload["values"]

    def _find_user_by_telegram_id(self, telegram_user_id: str) -> dict | None:
        search_payload = {
            "filter": {
                "operator": "and",
                "conditions": [
                    {
                        "field": "Telegram ID",
                        "operator": "eq",
                        "value": str(telegram_user_id),
                    }
                ],
            },
            "limit": 1,
        }

        response_json = self._request(
            method="POST",
            path=f"/catalogs/{self.users_catalog_id}/records/search",
            json=search_payload,
        )

        records = response_json.get("records") or response_json.get("data") or []
        if not records:
            return None
        return records[0]

    def _extract_field(self, record: dict, field_name: str):
        values = record.get("values") or record.get("fields") or {}
        return values.get(field_name)

    def _extract_linked_id(self, value) -> int | None:
        if isinstance(value, dict):
            linked_id = value.get("id")
            return int(linked_id) if linked_id is not None else None
        if isinstance(value, list) and value:
            first = value[0]
            if isinstance(first, dict) and first.get("id") is not None:
                return int(first["id"])
        return None

    def _request(self, method: str, path: str, json: dict | None = None) -> dict:
        self._ensure_authenticated()

        api_path = f"/api/v1{path}"
        try:
            response = self._session.request(
                method=method,
                url=api_path,
                json=json,
            )
            response.raise_for_status()
            return response.json() if response.text else {}
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            body = exc.response.text
            raise BpiumAPIError(f"Bpium API вернул ошибку {status}: {body}") from exc
        except httpx.RequestError as exc:
            raise BpiumAPIError(f"Bpium API недоступен: {exc}") from exc
        except ValueError as exc:
            raise BpiumAPIError(f"Bpium API вернул невалидный JSON: {exc}") from exc

    def _ensure_authenticated(self) -> None:
        if self._is_authenticated:
            return

        auth_payload = {
            "email": self.login,
            "password": self.password,
        }

        try:
            response = self._session.post(
                "/auth/login",
                json=auth_payload,
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise BpiumAPIError(
                f"Ошибка авторизации в Bpium API ({exc.response.status_code}): {exc.response.text}"
            ) from exc
        except httpx.RequestError as exc:
            raise BpiumAPIError(f"Bpium API недоступен при авторизации: {exc}") from exc

        # После /auth/login используем сессионную cookie, которую хранит self._session.
        self._is_authenticated = True

    def _read_required_env(self, name: str) -> str:
        value = os.getenv(name, "").strip()
        if not value:
            raise BpiumAPIError(f"Не задана env-переменная {name}")
        return value

    def _read_required_int_env(self, name: str) -> int:
        raw_value = self._read_required_env(name)
        try:
            return int(raw_value)
        except ValueError as exc:
            raise BpiumAPIError(f"env-переменная {name} должна быть целым числом") from exc

    # Ниже оставлены методы каркаса, чтобы не ломать остальные потоки MVP-скелета.
    def save_note(self, user_context: dict, source_type: str, content_text: str) -> dict:
        now = datetime.now(KRASNOYARSK_TZ)
        return {
            "note_id": "stub",
            "tenant_id": user_context["tenant_id"],
            "user_id": user_context["user_id"],
            "source_type": source_type,
            "content_text": content_text,
            "created_at": now.isoformat(),
        }

    def list_notes(self, user_context: dict) -> list[dict]:
        return []

    def search_notes_text(self, user_context: dict, query: str) -> list[dict]:
        return []

    def save_daily_summary(self, user_context: dict, summary_text: str) -> dict:
        now = datetime.now(KRASNOYARSK_TZ)
        summary = {
            "summary_id": f"s-{len(self._summaries) + 1}",
            "tenant_id": user_context["tenant_id"],
            "user_id": user_context["user_id"],
            "date": now.strftime("%Y-%m-%d"),
            "summary_text": summary_text,
            "created_at": now.isoformat(),
        }
        self._summaries.append(summary)
        return summary

    def transcribe_voice(self, voice_payload: dict) -> str:
        duration = voice_payload.get("duration", "?")
        return f"[voice transcript placeholder, duration={duration}s]"
