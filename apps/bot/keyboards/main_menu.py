"""Минимальная клавиатура главного меню."""


def build_main_menu() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "Собрать summary дня", "callback_data": "daily_summary"}],
            [{"text": "Заметки", "callback_data": "notes"}],
            [{"text": "Найти заметку", "callback_data": "find_note"}],
        ]
    }
