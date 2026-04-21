#!/bin/bash
# DeepChan One-Click Installer for Ubuntu 22.04/24.04
# Run as root or with sudo

set -e
PROJECT_DIR="/opt/deepchan"

echo "🚀 Установка DeepChan..."

# 1. Системные пакеты
apt update
apt install -y python3 python3-venv python3-pip ffmpeg sqlite3 git

# 2. Создаём пользователя
if ! id -u deepchan &>/dev/null; then
    useradd --system --no-create-home --shell /bin/false deepchan
fi

# 3. Клонируем репо, если запущено не из него
if [ ! -f "$PROJECT_DIR/app.py" ]; then
    git clone https://github.com/yogannnn/deepchan.git "$PROJECT_DIR"
fi
cd "$PROJECT_DIR"

# 4. Виртуальное окружение
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 5. Конфигурация
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
mkdir -p logs
chown deepchan:deepchan logs
touch logs/board.log
chown deepchan:deepchan logs/board.log
mkdir -p static/{uploads,radio/playlist} instance
chown -R deepchan:deepchan "$PROJECT_DIR"
chmod 755 static/{uploads,radio}

# 7. Инициализируем БД и дефолтные настройки
chown -R deepchan:deepchan instance
source .venv/bin/activate
python << 'PYTHON_SCRIPT'
from app import app, db
from models import Setting, Board

with app.app_context():
    db.create_all()
    
    defaults = {
        'SITE_TITLE': 'DeepChan',
        'THREADS_PER_PAGE': '30',
        'POSTS_PER_PAGE': '50',
        'MAX_FILES': '4',
        'ALLOWED_EXTENSIONS': 'jpg,jpeg,png,gif,webm,mp4,mp3,ogg,flac,wav,m4a',
        'MAX_CONTENT_LENGTH': str(10 * 1024 * 1024),
        'MAX_IMAGE_DIMENSION': '5000',
        'MAX_VIDEO_DURATION': '180',
        'MAX_VIDEO_SIZE': str(50 * 1024 * 1024),
        'MAX_AUDIO_DURATION': '600',
        'MAX_AUDIO_SIZE': str(30 * 1024 * 1024),
        'WEBP_CONVERT_ENABLED': 'True',
        'STEALTH_TRIM': 'True',
        'RADIO_ENABLED': 'True',
        'RADIO_BITRATE': '128k',
        'CAPTCHA_ENABLED': 'False',
        'AUTO_REFRESH_ENABLED': 'True',
        'AUTO_REFRESH_INTERVAL': '30',
        'RATE_LIMIT_SECONDS': '30',
        'STATS_SHOW_IPS': 'False',
        'BOARD_CLOSED': 'False',
        'HEADER_HTML': r'''<div style="background: #0d140d; border-bottom: 1px solid #2a6e2a; padding: 8px 15px; display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center;">
    <div>
        <a href="/" style="color: #66ff66; margin-right: 20px; text-decoration: none;">🏠 Главная</a>
        <a href="/catalog" style="color: #b3ffb3; margin-right: 20px; text-decoration: none;">🖼️ Каталог</a>
        <a href="/search" style="color: #b3ffb3; margin-right: 20px; text-decoration: none;">🔎 Поиск</a>
        <a href="/radio" style="color: #66ff66; text-decoration: none;">📻 Анон-радио</a>
    </div>
    <span style="color: #7ab37a;">DeepChan</span>
</div>''',
        'FOOTER_HTML': r'''<div style="margin-top: 30px; padding: 15px 0; border-top: 1px solid #1e3b1e; text-align: center; color: #7ab37a; font-size: 0.85rem;">
        <p>
            <a href="/" style="color: #66ff66;">Главная</a> | 
            <a href="/admin" style="color: #66ff66;">Админка</a> | 
            <a href="/bbcode" style="color: #66ff66;">BB-коды</a> | 
            <span>Powered by DeepChan</span>
        </p>
        <p style="margin-top: 10px;">
            <span style="background: #0d140d; padding: 3px 8px; border-radius: 4px; border: 1px solid #2a4a2a;">i2p ready</span>
        </p>
    </div>''',
        'ANNOUNCEMENT_HTML': r'''<div style="background: #0d140d; border: 1px solid #2a6e2a; border-radius: 8px; padding: 15px; margin-top: 20px; color: #b3ffb3; text-align: center;">
    <p style="margin: 0 0 10px 0; font-size: 1.1rem;">
        <strong>DeepChan</strong> живёт на ваших донатах
    </p>
    <p style="margin: 0 0 10px 0; opacity: 0.9;">
        Сервера, электричество и анонимность требуют ресурсов.<br>
        Если борда была полезной — поддержите проект.
    </p>
    <p style="margin: 0; font-family: monospace; word-break: break-all; background: #0a0f0a; padding: 8px; border-radius: 4px; border: 1px solid #1e3b1e;">
        <span style="color: #66ff66;">XMR:</span><br>
        46FeqKBPTtWE3NwYUdyFHLjP87yb26NKA8UHqkTuJ8YBf4ZjhNTAV7VLW4op3zwcc6JhgQNnfz4EV7Rtws4rrWq2GAKMBZu
    </p>
    <p style="margin: 10px 0 0 0; font-size: 0.85rem; opacity: 0.7;">
        Спасибо, что остаётесь анонимными.
    </p>
</div>''',
    }
    for key, value in defaults.items():
        if not Setting.query.get(key):
            db.session.add(Setting(key=key, value=value))
    
    if not Board.query.filter_by(short_name='b').first():
        db.session.add(Board(short_name='b', name='Бред', description='Общий раздел'))
    
    db.session.commit()
    print("✅ Дефолтные настройки и доска /b/ созданы")
PYTHON_SCRIPT

# 8. Systemd сервис
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

echo "✅ Установка завершена!"
echo "Сайт: http://$(hostname -I | awk '{print $1}'):5000"
echo "Админка: логин admin, пароль admin (смените в .env)"
