#!/bin/bash
# migrate_board_to_settings.sh

cd /opt/deepchan

sed -i \
    -e "s/current_app\.config\.get(\"THREADS_PER_PAGE\", 50)/current_app.config[\"SETTINGS\"].threads_per_page/g" \
    -e "s/current_app\.config\.get(\"THREADS_PER_PAGE\", 30)/current_app.config[\"SETTINGS\"].threads_per_page/g" \
    -e "s/current_app\.config\.get(\"POSTS_PER_PAGE\", 50)/current_app.config[\"SETTINGS\"].posts_per_page/g" \
    -e "s/current_app\.config\.get(\"CAPTCHA_ENABLED\", False)/current_app.config[\"SETTINGS\"].captcha_enabled/g" \
    -e "s/current_app\.config\.get(\"CAPTCHA_ENABLED\")/current_app.config[\"SETTINGS\"].captcha_enabled/g" \
    -e "s/current_app\.config\.get(\"RADIO_ENABLED\", False)/current_app.config[\"SETTINGS\"].radio_enabled/g" \
    -e "s/current_app\.config\.get(\"REPORTS_ENABLED\", True)/current_app.config[\"SETTINGS\"].reports_enabled/g" \
    -e "s/current_app\.config\.get(\"ADMIN_TRIP_SECRET\", \"\")/current_app.config[\"SETTINGS\"].admin_trip_secret/g" \
    -e "s/current_app\.config\.get(\"SITE_URL\", \"http:\/\/127.0.0.1:5000\")/current_app.config[\"SETTINGS\"].site_url/g" \
    -e "s/current_app\.config\.get(\"SITE_URL\", \"http:\/\/deepchan.i2p\")/current_app.config[\"SETTINGS\"].site_url/g" \
    blueprints/board.py

echo "Замены в board.py выполнены."
