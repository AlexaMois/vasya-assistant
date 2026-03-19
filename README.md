# vasya-assistant

Каркас первого рабочего MVP Telegram-бота без лишней сложности.

## Что уже заложено в каркас

- Telegram webhook
- Обработчик `/start`
- Проверка пользователя в Bpium
- Заготовки для приёма:
  - TXT
  - text notes
  - voice notes
- Кнопки:
  - `Собрать summary дня`
  - `Заметки`
  - `Найти заметку`
- Bpium API client
- Базовые слои:
  - Telegram layer
  - backend logic
  - Bpium integration

## Структура проекта

```text
vasya-assistant/
  pyproject.toml
  .env.example
  README.md
  apps/
    bot/
      main.py                        # Точка входа webhook
      handlers/
        dispatcher.py                # Роутинг update по типам событий
        start.py                     # /start
        notes.py                     # TXT/text/voice handlers
        search.py                    # Поиск заметки (заготовка)
      keyboards/
        main_menu.py                 # Кнопки: summary/notes/find

    backend/
      notes_service.py               # Логика заметок + text search
      summary_service.py             # Логика summary дня

    integrations/
      bpium/
        client.py                    # Bpium API client
```

## Где точка входа

- `apps/bot/main.py`
  - `POST /telegram/webhook` — входящий webhook от Telegram.
  - `GET /health` — healthcheck.

## Реальная интеграция Bpium API для text notes

### Нужные env

- `BPIUM_BASE_URL`
- `BPIUM_LOGIN`
- `BPIUM_PASSWORD`
- `BPIUM_USERS_CATALOG_ID=66`
- `BPIUM_NOTES_CATALOG_ID=67`
- `BPIUM_COMPANIES_CATALOG_ID=65`
- `BPIUM_COMMAND_LOG_CATALOG_ID=70`
- `BPIUM_TIMEOUT_SEC` (по умолчанию `15`)

### Endpoint поиска пользователя

`POST /api/catalogs/{BPIUM_USERS_CATALOG_ID}/records/search`

Поиск идёт по полю `Telegram ID`.

### Endpoint создания заметки

`POST /api/catalogs/{BPIUM_NOTES_CATALOG_ID}/records`

### Payload создания заметки

```json
{
  "values": {
    "Заголовок": "Первые 80 символов текста",
    "Текст заметки": "Полный текст заметки",
    "Автор": {"id": 123, "catalog_id": 66},
    "Компания": {"id": 45, "catalog_id": 65},
    "Тип источника": "текст",
    "Дата создания": "2026-03-19 14:20:33",
    "Статус заметки": "активна",
    "Telegram message_id": null,
    "Исходный текст распознавания": "Полный текст заметки"
  }
}
```

`Дата создания` всегда формируется в timezone `Asia/Krasnoyarsk`.

### Ошибки Bpium API

Если API недоступен или вернул ошибку, бот возвращает понятный ответ вида:

`Не удалось сохранить заметку: ...`

и не падает молча.

## Что НЕ сделано специально (вне MVP-каркаса)

- Нет workers
- Нет semantic search
- Нет сложной инфраструктуры
- Нет legacy-модулей

## Быстрый запуск (локально)

```bash
uvicorn apps.bot.main:app --reload --port 8000
```

## Где проект читает env

Env читаются в `BpiumClient.__init__` в файле `apps/integrations/bpium/client.py`:
- `BPIUM_BASE_URL`
- `BPIUM_LOGIN`
- `BPIUM_PASSWORD`
- `BPIUM_USERS_CATALOG_ID`
- `BPIUM_NOTES_CATALOG_ID`
- `BPIUM_COMPANIES_CATALOG_ID`
- `BPIUM_COMMAND_LOG_CATALOG_ID`
- `BPIUM_TIMEOUT_SEC`

Валидация обязательных env выполнена методами `_read_required_env` и `_read_required_int_env`.
