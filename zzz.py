#!/usr/bin/env python3
import re

file_path = "tests/test_plugin_identity_captcha.py"

with open(file_path, "r") as f:
    content = f.read()

# 1. Добавляем импорт text и inspect, если их нет
if "from sqlalchemy import text" not in content:
    content = content.replace(
        "from models import db as _db, Board, Thread, Post",
        "from sqlalchemy import text, inspect\nfrom models import db as _db, Board, Thread, Post",
    )

# 2. Ищем место после _db.create_all() и до # Создаём базовые объекты
# Вставляем создание таблицы
pattern = r"(_db\.create_all\(\)\s+)(\# Создаём базовые объекты)"
replacement = r'\1        inspector = inspect(_db.engine)\n        if "user_preferences" not in inspector.get_table_names():\n            _db.session.execute(text("""\n                CREATE TABLE IF NOT EXISTS user_preferences (\n                    identity_hash TEXT PRIMARY KEY,\n                    language TEXT DEFAULT \'ru\',\n                    hidden_boards TEXT DEFAULT \'\',\n                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,\n                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n                )\n            """))\n            _db.session.commit()\n\n        \2'
new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open(file_path, "w") as f:
    f.write(new_content)

print("✅ Файл исправлен. Запустите pytest tests/test_plugin_identity_captcha.py -v")
