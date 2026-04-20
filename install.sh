#!/bin/bash
# DeepChan Radio Installer for Ubuntu 22.04/24.04
# Run as root or with sudo

set -e

echo "🚀 DeepChan Installation Script"
echo "================================"

# Проверка прав
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root or with sudo"
    exit 1
fi

# 1. Установка системных зависимостей
echo "📦 Installing system packages..."
apt update
apt install -y python3 python3-venv python3-pip git wget curl \
    icecast2 ffmpeg sqlite3 sudo

# 2. Создание пользователя icecast (если нет)
if ! id icecast &>/dev/null; then
    useradd --system --no-create-home --shell /bin/false icecast
    echo "✅ User icecast created"
else
    echo "✅ User icecast already exists"
fi

# 3. Настройка директорий проекта
PROJECT_DIR="/opt/deepchan"
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ Project directory $PROJECT_DIR not found. Please clone repository first."
    exit 1
fi
cd "$PROJECT_DIR"

# 4. Создание виртуального окружения Python
echo "🐍 Setting up Python virtual environment..."
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install waitress  # для production

# 5. Создание необходимых директорий
echo "📁 Creating directories..."
mkdir -p static/uploads
mkdir -p static/radio/playlist
mkdir -p static/radio/icecast/{logs,web,admin}
mkdir -p instance

# 6. Настройка прав
chown -R www-data:www-data "$PROJECT_DIR" 2>/dev/null || chown -R root:root "$PROJECT_DIR"
chown -R icecast:icecast static/radio
chmod -R 755 static/radio

# 7. Инициализация базы данных
echo "💾 Initializing database..."
if [ ! -f instance/board.db ]; then
    python -c "from app import app, db; app.app_context().push(); db.create_all()"
    echo "✅ Database created"
else
    echo "✅ Database already exists"
fi

# 8. Создание .env файла (если нет)
if [ ! -f .env ]; then
    cat > .env << 'EOF'
SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
ADMIN_PASSWORD=admin
DEPLOY_MODE=production
EOF
    echo "✅ .env file created with random SECRET_KEY"
fi

# 9. Настройка Icecast
echo "📻 Configuring Icecast..."
cat > /etc/icecast2/icecast.xml << 'EOF'
<icecast>
    <limits>
        <clients>100</clients>
        <sources>2</sources>
        <queue-size>524288</queue-size>
        <client-timeout>30</client-timeout>
        <header-timeout>15</header-timeout>
        <source-timeout>10</source-timeout>
        <burst-size>65535</burst-size>
    </limits>
    <authentication>
        <source-password>deepchanradio</source-password>
        <admin-password>deepchanadmin</admin-password>
    </authentication>
    <hostname>0.0.0.0</hostname>
    <listen-socket>
        <port>8000</port>
        <bind-address>0.0.0.0</bind-address>
    </listen-socket>
    <paths>
        <basedir>/opt/deepchan/static/radio</basedir>
        <logdir>/opt/deepchan/static/radio/icecast/logs</logdir>
        <webroot>/opt/deepchan/static/radio/icecast/web</webroot>
        <adminroot>/opt/deepchan/static/radio/icecast/admin</adminroot>
        <pidfile>/opt/deepchan/static/radio/icecast/icecast.pid</pidfile>
    </paths>
    <logging>
        <accesslog>access.log</accesslog>
        <errorlog>error.log</errorlog>
        <loglevel>3</loglevel>
    </logging>
    <security>
        <chroot>0</chroot>
        <changeowner>
            <user>icecast</user>
            <group>icecast</group>
        </changeowner>
    </security>
    <mount type="normal">
        <mount-name>/stream</mount-name>
        <stream-name>DeepChan Radio</stream-name>
        <stream-description>User uploaded music</stream-description>
        <genre>Various</genre>
        <public>0</public>
    </mount>
    <playlist>
        <file>/opt/deepchan/static/radio/playlist.txt</file>
        <shuffle>1</shuffle>
    </playlist>
</icecast>
EOF

# Включаем запуск Icecast
sed -i 's/ENABLE=false/ENABLE=true/' /etc/default/icecast2
systemctl enable icecast2
systemctl restart icecast2
echo "✅ Icecast configured and started"

# 10. Создание systemd сервиса для Flask
echo "⚙️ Creating systemd service for Flask..."
cat > /etc/systemd/system/deepchan.service << EOF
[Unit]
Description=DeepChan Imageboard
After=network.target

[Service]
User=root
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/.venv/bin"
ExecStart=$PROJECT_DIR/.venv/bin/python app.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable deepchan.service
systemctl start deepchan.service
echo "✅ DeepChan service started"

# 11. Создание скрипта управления радио
cat > /usr/local/bin/deepchan-radio << 'EOF'
#!/bin/bash
case "$1" in
    start)   systemctl start icecast2 ;;
    stop)    systemctl stop icecast2 ;;
    restart) systemctl restart icecast2 ;;
    reload)  systemctl reload icecast2 ;;
    status)  systemctl status icecast2 ;;
    *)       echo "Usage: deepchan-radio {start|stop|restart|reload|status}" ;;
esac
EOF
chmod +x /usr/local/bin/deepchan-radio

# 12. Финальные проверки
echo ""
echo "🎉 Installation complete!"
echo "=========================="
echo "Flask: http://$(hostname -I | awk '{print $1}'):5000"
echo "Radio stream: http://$(hostname -I | awk '{print $1}'):8000/stream"
echo "Admin login: admin / admin (change password in .env)"
echo ""
echo "To manage services:"
echo "  systemctl status deepchan icecast2"
echo "  deepchan-radio {start|stop|restart|reload|status}"
