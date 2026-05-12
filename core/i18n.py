import json
from pathlib import Path

from flask import request

BASE_DIR = Path(__file__).resolve().parent.parent
TRANSLATIONS_DIR = BASE_DIR / "translations"


def get_locale():
    lang = request.args.get("lang", "ru")
    if lang not in ("ru", "en"):
        lang = "ru"
    return lang


def load_translations(lang="ru"):
    path = TRANSLATIONS_DIR / f"{lang}.json"
    if not path.exists():
        path = TRANSLATIONS_DIR / "ru.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def t(key):
    try:
        lang = get_locale()
    except Exception:
        lang = "ru"
    try:
        translations = load_translations(lang)
        return translations.get(key, key)
    except Exception:
        return key
