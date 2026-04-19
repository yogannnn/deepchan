#!/bin/bash
# video_part2.sh — полная замена utils.py с поддержкой видео

cd ~/deepchan
source .venv/bin/activate

echo "🎬 Часть 2: Обновляем utils.py для обработки видео..."

# Сделаем бэкап
cp utils.py utils_backup_video.py

cat > utils.py << 'EOF'
import os
import secrets
import re
import time
import hashlib
import hmac
import random
import io
import html
import subprocess
import json
from PIL import Image, UnidentifiedImageError
from flask import current_app, request, abort
from models import Post

_last_post_time = {}

def check_rate_limit():
    ip = request.remote_addr
    now = time.time()
    if ip in _last_post_time:
        elapsed = now - _last_post_time[ip]
        if elapsed < current_app.config.get('RATE_LIMIT_SECONDS', 30):
            abort(429, description=f"Слишком часто. Подождите {current_app.config.get('RATE_LIMIT_SECONDS', 30) - int(elapsed)} сек.")
    _last_post_time[ip] = now

def check_ban(ip):
    from models import Ban
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    ban = Ban.query.filter(
        Ban.ip_pattern == ip,
        Ban.active == True,
        (Ban.expires_at == None) | (Ban.expires_at > now)
    ).first()
    if ban:
        abort(403, description=f"Вы забанены. Причина: {ban.reason or 'не указана'}")

def apply_word_filters(text):
    from models import WordFilter
    filters = WordFilter.query.filter_by(active=True).all()
    for f in filters:
        if f.is_regex:
            if re.search(f.pattern, text, re.IGNORECASE):
                if f.action == 'block':
                    abort(400, description=f"Сообщение содержит запрещённое выражение: {f.pattern}")
                elif f.action == 'replace':
                    text = re.sub(f.pattern, f.replacement, text, flags=re.IGNORECASE)
        else:
            if f.pattern.lower() in text.lower():
                if f.action == 'block':
                    abort(400, description=f"Сообщение содержит запрещённое слово: {f.pattern}")
                elif f.action == 'replace':
                    text = text.replace(f.pattern, f.replacement)
    return text

def get_video_duration(filepath):
    """Возвращает длительность видео в секундах или None при ошибке."""
    try:
        result = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'json', filepath],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return float(data['format']['duration'])
    except Exception:
        pass
    return None

def generate_video_thumbnail(video_path, thumb_path, width=200):
    """Извлекает кадр из видео и сохраняет как WEBP."""
    try:
        subprocess.run(
            ['ffmpeg', '-i', video_path, '-ss', '00:00:01', '-vframes', '1',
             '-vf', f'scale={width}:-1', '-y', thumb_path],
            capture_output=True, timeout=15, check=True
        )
        return True
    except Exception:
        return False

def save_files(files):
    saved = []
    if not files:
        return saved

    max_files = current_app.config.get('MAX_FILES', 4)
    if len(files) > max_files:
        abort(400, description=f"Слишком много файлов (максимум {max_files})")

    max_image_dimension = current_app.config.get('MAX_IMAGE_DIMENSION', 5000)
    max_video_duration = current_app.config.get('MAX_VIDEO_DURATION', 180)
    max_video_size = current_app.config.get('MAX_VIDEO_SIZE', 50 * 1024 * 1024)
    webp_enabled = current_app.config.get('WEBP_CONVERT_ENABLED', True)
    stealth_trim = current_app.config.get('STEALTH_TRIM', True)
    allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', ['jpg','jpeg','png','gif','webp','mp4','webm','mov'])

    for idx, f in enumerate(files):
        if f.filename == '':
            continue

        ext = os.path.splitext(f.filename)[1].lower().lstrip('.')
        if ext not in allowed_extensions:
            abort(400, description=f"Недопустимый формат: {ext}")

        f.stream.seek(0, os.SEEK_END)
        file_size = f.tell()
        f.stream.seek(0)

        video_exts = {'mp4', 'webm', 'mov', 'avi', 'mkv'}
        is_video = ext in video_exts

        if is_video:
            if file_size > max_video_size:
                abort(400, description=f"Видео слишком большое (макс {max_video_size//1024//1024} МБ)")

            video_tmp = os.path.join(current_app.config['UPLOAD_FOLDER'], secrets.token_hex(16) + '.' + ext)
            f.save(video_tmp)

            duration = get_video_duration(video_tmp)
            if duration is None or duration > max_video_duration:
                os.remove(video_tmp)
                abort(400, description=f"Видео слишком длинное (макс {max_video_duration} сек)")

            random_hex = secrets.token_hex(16)
            picture_fn = random_hex + '.' + ext
            picture_path = os.path.join(current_app.config['UPLOAD_FOLDER'], picture_fn)
            os.rename(video_tmp, picture_path)

            thumb_fn = random_hex + '_thumb.webp'
            thumb_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'thumbs', thumb_fn)
            if not generate_video_thumbnail(picture_path, thumb_path):
                thumb_fn = None
                thumb_path = None

            f.stream.seek(0)
            file_data = f.read()
            sha256 = hashlib.sha256(file_data).hexdigest()

            saved.append((picture_fn, thumb_fn, idx, file_size, sha256, 'video', duration))

        else:
            # --- Обработка изображений (как раньше) ---
            try:
                f.stream.seek(0)
                img = Image.open(f.stream)
                img.verify()
            except (UnidentifiedImageError, Exception) as e:
                abort(400, description=f"Некорректный файл изображения: {str(e)}")

            f.stream.seek(0)
            img = Image.open(f.stream)

            if img.width > max_image_dimension or img.height > max_image_dimension:
                abort(400, description=f"Разрешение превышает {max_image_dimension}x{max_image_dimension}")

            is_animated_gif = False
            if img.format == 'GIF':
                try:
                    img.seek(1)
                    is_animated_gif = True
                except EOFError:
                    pass
                finally:
                    img.seek(0)

            if stealth_trim and (img.width > 2000 or img.height > 2000):
                img.thumbnail((2000, 2000), Image.LANCZOS)

            random_hex = secrets.token_hex(16)
            if webp_enabled and not is_animated_gif:
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGB")
                ext = ".webp"
                picture_fn = random_hex + ext
                picture_path = os.path.join(current_app.config['UPLOAD_FOLDER'], picture_fn)
                img.save(picture_path, format="WEBP", quality=85, method=6, save_all=False)
            else:
                ext = os.path.splitext(f.filename)[1].lower()
                if ext == '.jpg':
                    ext = '.jpeg'
                elif is_animated_gif:
                    ext = '.gif'
                picture_fn = random_hex + ext
                picture_path = os.path.join(current_app.config['UPLOAD_FOLDER'], picture_fn)

                if img.mode in ('RGBA', 'P') and not is_animated_gif:
                    img = img.convert('RGB')
                save_kwargs = {'optimize': True, 'quality': 85}
                if not is_animated_gif:
                    save_kwargs['exif'] = Image.Exif()
                    img.save(picture_path, **save_kwargs)
                else:
                    img.save(picture_path, save_all=True, loop=0, **save_kwargs)

            file_size = os.path.getsize(picture_path)

            thumb_fn = random_hex + "_thumb" + (".webp" if webp_enabled and not is_animated_gif else ext)
            thumb_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'thumbs', thumb_fn)
            try:
                thumb_img = Image.open(picture_path)
                if thumb_img.mode not in ("RGB", "RGBA"):
                    thumb_img = thumb_img.convert("RGB")
                thumb_img.thumbnail((200, 200))
                if webp_enabled:
                    thumb_img.save(thumb_path, format="WEBP", quality=80, method=6)
                else:
                    thumb_img.save(thumb_path, optimize=True, quality=80)
            except Exception:
                thumb_fn = None

            f.stream.seek(0)
            file_data = f.read()
            sha256 = hashlib.sha256(file_data).hexdigest()

            saved.append((picture_fn, thumb_fn, idx, file_size, sha256, 'image', None))

    return saved

def parse_bbcode(text):
    text = re.sub(r'\[b\](.*?)\[/b\]', r'<strong>\1</strong>', text, flags=re.IGNORECASE|re.DOTALL)
    text = re.sub(r'\[i\](.*?)\[/i\]', r'<em>\1</em>', text, flags=re.IGNORECASE|re.DOTALL)
    text = re.sub(r'\[u\](.*?)\[/u\]', r'<u>\1</u>', text, flags=re.IGNORECASE|re.DOTALL)
    text = re.sub(r'\[s\](.*?)\[/s\]', r'<del>\1</del>', text, flags=re.IGNORECASE|re.DOTALL)
    text = re.sub(r'\[spoiler\](.*?)\[/spoiler\]', r'<details class="spoiler"><summary>Спойлер</summary>\1</details>', text, flags=re.IGNORECASE|re.DOTALL)
    text = re.sub(r'\[code\](.*?)\[/code\]', r'<pre><code>\1</code></pre>', text, flags=re.IGNORECASE|re.DOTALL)
    return text

def process_urls(text):
    def magnet_replace(match):
        url = match.group(0)
        return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{url}</a>'
    text = re.sub(r'magnet:\?[^\s<>"\']+', magnet_replace, text, flags=re.IGNORECASE)

    def url_replace(match):
        url = match.group(0)
        if re.search(r'^(https?://)?(127\.0\.0\.1|\[::1\]|::1)([/:]|$)', url, re.IGNORECASE):
            if not url.startswith('http://') and not url.startswith('https://'):
                url = 'http://' + url
            return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{match.group(0)}</a>'
        if re.search(r'\.(i2p|onion)(/|$)', url, re.IGNORECASE):
            if not url.startswith('http://') and not url.startswith('https://'):
                url = 'http://' + url
            return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{match.group(0)}</a>'
        return f'{match.group(0)}<span class="clearnet-warning">ClearNet</span>'

    text = re.sub(r'''(?i)\b((?:https?://|ftp://)?[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:[a-z]{2,}|i2p|onion)(?:/[^\s<>"']*)?)\b''', url_replace, text)
    text = re.sub(r'''(?i)\b((?:https?://|ftp://)?(?:[0-9]{1,3}\.){3}[0-9]{1,3})(?::[0-9]+)?(?:/[^\s<>"']*)?\b''', url_replace, text)
    return text

def process_comment(text, board_name, thread_id):
    text = html.escape(text)
    text = text.replace('&gt;&gt;', '>>')
    text = text.replace('&#91;', '[').replace('&#93;', ']')

    def replace_quote(match):
        num = match.group(1)
        quoted_post = Post.query.filter_by(id=num, thread_id=thread_id).first()
        if quoted_post:
            quote_text = html.escape(quoted_post.comment)
            if len(quote_text) > 200:
                quote_text = quote_text[:200] + "..."
            return f'<blockquote class="inline-quote"><a href="{current_app.url_for("thread", board_name=board_name, thread_id=thread_id)}#post{num}">&gt;&gt;{num}</a> {quote_text}</blockquote>'
        return match.group(0)

    text = re.sub(r'>>(\d+)', replace_quote, text)
    text = parse_bbcode(text)
    text = process_urls(text)
    return text

def generate_captcha():
    from captcha.image import ImageCaptcha
    image = ImageCaptcha(width=280, height=90)
    captcha_text = ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=5))
    data = image.generate(captcha_text)
    return data, captcha_text

# ===== CSRF =====
def generate_csrf_token(user_id, action, secret_key, timestamp=None):
    if timestamp is None:
        timestamp = int(time.time())
    message = f"{user_id}:{action}:{timestamp}"
    token = hmac.new(secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()
    return token, timestamp

def verify_csrf_token(user_id, action, token, timestamp, secret_key, max_age=600):
    if int(time.time()) - int(timestamp) > max_age:
        return False
    expected_token, _ = generate_csrf_token(user_id, action, secret_key, timestamp)
    return hmac.compare_digest(expected_token, token)
EOF

echo "✅ Часть 2 завершена. utils.py обновлён."
