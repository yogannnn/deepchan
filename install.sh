#!/bin/bash
# DeepChan One-Click Installer for Ubuntu 22.04/24.04
# Run as root or with sudo
set -e
PROJECT_DIR="/opt/deepchan"
echo "🚀 Установка DeepChan..."

# 1. Системные пакеты
apt update
apt install -y python3 python3-venv python3-pip ffmpeg sqlite3 git

# 2. Создаём пользователя deepchan
if ! id -u deepchan &>/dev/null; then
    useradd --system --no-create-home --shell /bin/false deepchan
fi

# 3. Клонируем репо, если запущено не из него
if [ ! -f "$PROJECT_DIR/app.py" ]; then
    if [ -d "$PROJECT_DIR" ]; then
        # Если папка существует, но пуста — удалим её (или оставим, но git clone требует пустоту)
        rmdir "$PROJECT_DIR" 2>/dev/null || true
    fi
    git clone https://github.com/yogannnn/deepchan.git "$PROJECT_DIR"
fi
cd "$PROJECT_DIR"

# 4. Виртуальное окружение и зависимости
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 5. Конфигурация (.env)
if [ ! -f .env ]; then
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    cat > .env << ENV
SECRET_KEY=$SECRET_KEY
ADMIN_PASSWORD=admin
DEPLOY_MODE=production
RADIO_FOLDER=$PROJECT_DIR/static/radio
UPLOAD_FOLDER=$PROJECT_DIR/static/uploads
ENV
fi

# 6. Создаём папки и права
mkdir -p logs static/{uploads,radio/playlist,uploads/thumbs} instance
chown -R deepchan:deepchan "$PROJECT_DIR"
chmod -R 755 static/uploads static/radio

# 7. Инициализируем БД и дефолтные настройки одним вызовом
source .venv/bin/activate
python << 'PYTHON_SCRIPT'
from app import app, db
from migrate import run_migrations
from models import Setting, Board
from core.settings import Settings

with app.app_context():
    # Создаём/обновляем таблицы
    run_migrations(app)

    # Заполняем настройки из DEFAULTS, если их ещё нет
    settings = Settings(app)  # временно, чтобы взять DEFAULTS
    for key, value in Settings.DEFAULTS.items():
        if not Setting.query.get(key):
            db.session.add(Setting(key=key, value=str(value)))

    # Добавляем дефолтную доску /b/
    if not Board.query.filter_by(short_name='b').first():
        db.session.add(Board(short_name='b', name='Бред', description='Общий раздел'))

    db.session.commit()
PYTHON_SCRIPT

# 8. Systemd сервис (если ещё не настроен)
if [ ! -f /etc/systemd/system/deepchan.service ]; then
    cat > /etc/systemd/system/deepchan.service << SYSTEMD
[Unit]
Description=DeepChan Imageboard
After=network.target

[Service]
User=deepchan
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/.venv/bin"
ExecStart=$PROJECT_DIR/.venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
SYSTEMD
    systemctl daemon-reload
    systemctl enable deepchan
    systemctl start deepchan
else
    systemctl restart deepchan
fi

echo "✅ Установка завершена!"
echo "Сайт: http://$(hostname -I | awk '{print $1}'):5000"
echo "Админка: логин admin, пароль admin (смените в .env)"
