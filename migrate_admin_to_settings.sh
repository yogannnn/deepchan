#!/bin/bash
# migrate_admin_to_settings.sh – полный переход admin.py на Settings

cd /opt/deepchan

# 1. Заменяем все current_app.config.get и app.config на Settings
sed -i \
    -e 's/current_app\.config\.get("ADMIN_PASSWORD", current_app\.config\.get("ADMIN_PASSWORD", "admin")/current_app.config["SETTINGS"].admin_password/g' \
    -e 's/current_app\.config\.get("ADMIN_PASSWORD", "admin")/current_app.config["SETTINGS"].admin_password/g' \
    -e 's/current_app\.config\.get("ADMIN_TRIP_SECRET", "")/current_app.config["SETTINGS"].admin_trip_secret/g' \
    -e 's/current_app\.config\.get("DEPLOY_MODE", "production")/current_app.config["SETTINGS"].deploy_mode/g' \
    -e 's/current_app\.config\.get("SITE_TITLE", "Имиджборда")/current_app.config["SETTINGS"].site_title/g' \
    -e 's/current_app\.config\.get("THREADS_PER_PAGE", 30)/current_app.config["SETTINGS"].threads_per_page/g' \
    -e 's/current_app\.config\.get("THREADS_PER_PAGE", 50)/current_app.config["SETTINGS"].threads_per_page/g' \
    -e 's/current_app\.config\.get("POSTS_PER_PAGE", 50)/current_app.config["SETTINGS"].posts_per_page/g' \
    -e 's/current_app\.config\.get("MAX_FILES", 4)/current_app.config["SETTINGS"].max_files/g' \
    -e 's/current_app\.config\.get("ALLOWED_EXTENSIONS", '\''\['\''jpg'\'', '\''jpeg'\'', '\''png'\'', '\''gif'\''\]'\'')/current_app.config["SETTINGS"].allowed_extensions/g' \
    -e 's/current_app\.config\.get("MAX_CONTENT_LENGTH", 10 * 1024 * 1024)/current_app.config["SETTINGS"].max_content_length/g' \
    -e 's/current_app\.config\.get("MAX_IMAGE_DIMENSION", 5000)/current_app.config["SETTINGS"].max_image_dimension/g' \
    -e 's/current_app\.config\.get("MAX_VIDEO_DURATION", 180)/current_app.config["SETTINGS"].max_video_duration/g' \
    -e 's/current_app\.config\.get("MAX_VIDEO_SIZE", 50 * 1024 * 1024)/current_app.config["SETTINGS"].max_video_size/g' \
    -e 's/current_app\.config\.get("MAX_AUDIO_DURATION", 600)/current_app.config["SETTINGS"].max_audio_duration/g' \
    -e 's/current_app\.config\.get("MAX_AUDIO_SIZE", 30 * 1024 * 1024)/current_app.config["SETTINGS"].max_audio_size/g' \
    -e 's/current_app\.config\.get("WEBP_CONVERT_ENABLED", True)/current_app.config["SETTINGS"].webp_convert_enabled/g' \
    -e 's/current_app\.config\.get("STEALTH_TRIM", True)/current_app.config["SETTINGS"].stealth_trim/g' \
    -e 's/current_app\.config\.get("RADIO_ENABLED", False)/current_app.config["SETTINGS"].radio_enabled/g' \
    -e 's/current_app\.config\.get("RADIO_BITRATE", '\''128k'\'')/current_app.config["SETTINGS"].radio_bitrate/g' \
    -e 's/current_app\.config\.get("CAPTCHA_ENABLED", False)/current_app.config["SETTINGS"].captcha_enabled/g' \
    -e 's/current_app\.config\.get("AUTO_REFRESH_ENABLED", True)/current_app.config["SETTINGS"].auto_refresh_enabled/g' \
    -e 's/current_app\.config\.get("AUTO_REFRESH_INTERVAL", 30)/current_app.config["SETTINGS"].auto_refresh_interval/g' \
    -e 's/current_app\.config\.get("RATE_LIMIT_SECONDS", 30)/current_app.config["SETTINGS"].rate_limit_seconds/g' \
    -e 's/current_app\.config\.get("STATS_SHOW_IPS", False)/current_app.config["SETTINGS"].stats_show_ips/g' \
    -e 's/current_app\.config\.get("BOARD_CLOSED", False)/current_app.config["SETTINGS"].board_closed/g' \
    -e 's/current_app\.config\.get("REPORTS_ENABLED", True)/current_app.config["SETTINGS"].reports_enabled/g' \
    -e 's/current_app\.config\.get("HEADER_HTML", '\'\''\'\'')/current_app.config["SETTINGS"].header_html/g' \
    -e 's/current_app\.config\.get("FOOTER_HTML", '\'\''\'\'')/current_app.config["SETTINGS"].footer_html/g' \
    -e 's/current_app\.config\.get("ANNOUNCEMENT_HTML", '\'\''\'\'')/current_app.config["SETTINGS"].announcement_html/g' \
    -e 's/current_app\.config\.get("RADIO_FOLDER", "/root/deepchan/static/radio")/current_app.config["SETTINGS"].radio_folder/g' \
    -e 's/current_app\.config/"SETTINGS"/current_app.config["SETTINGS"]/g' \
    blueprints/admin.py

echo "✅ admin.py обновлён. Проверь тесты: pytest -v"
