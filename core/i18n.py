import json
from pathlib import Path

from flask import current_app

BASE_DIR = Path(__file__).resolve().parent.parent
TRANSLATIONS_DIR = BASE_DIR / "translations"


def get_default_lang():
    """Возвращает язык из глобальных настроек, fallback — ru."""
    try:
        return current_app.config["SETTINGS"].site_lang
    except (KeyError, RuntimeError):
        return "ru"


def load_translations(lang="ru"):
    path = TRANSLATIONS_DIR / f"{lang}.json"
    if not path.exists():
        path = TRANSLATIONS_DIR / "ru.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def t(key, lang=None):
    """Возвращает перевод для ключа. lang берётся из глобальной настройки, если не передан."""
    if lang is None:
        lang = get_default_lang()
    try:
        translations = load_translations(lang)
        return translations.get(key, key)
    except Exception:
        try:
            translations = load_translations("ru")
            return translations.get(key, key)
        except Exception:
            return key
