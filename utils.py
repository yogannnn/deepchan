import os
import secrets
import re
import time
import hashlib
import random
import io
import html
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
    from datetime import datetime
    now = datetime.utcnow()
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

def save_files(files):
    saved = []
    if not files:
        return saved

    max_files = current_app.config.get('MAX_FILES', 4)
    if len(files) > max_files:
        abort(400, description=f"Слишком много файлов (максимум {max_files})")

    max_dimension = current_app.config.get('MAX_IMAGE_DIMENSION', 5000)
    webp_enabled = current_app.config.get('WEBP_CONVERT_ENABLED', True)

    for idx, f in enumerate(files):
        if f.filename == '':
            continue

        # 1. Проверка размера
        f.stream.seek(0, os.SEEK_END)
        file_size = f.tell()
        f.stream.seek(0)
        if file_size > current_app.config.get('MAX_CONTENT_LENGTH', 10 * 1024 * 1024):
            abort(400, description="Файл слишком большой")

        # 2. Верификация
        try:
            f.stream.seek(0)
            img = Image.open(f.stream)
            img.verify()
        except (UnidentifiedImageError, Exception) as e:
            current_app.logger.warning(f"Image verification failed: {e}")
            abort(400, description="Некорректный файл изображения")

        # 3. Повторное открытие
        f.stream.seek(0)
        img = Image.open(f.stream)

        # 4. Проверка разрешения
        if img.width > max_dimension or img.height > max_dimension:
            abort(400, description=f"Разрешение превышает {max_dimension}x{max_dimension}")

        # 5. Определяем, анимированный ли GIF
        is_animated_gif = False
        if img.format == 'GIF':
            try:
                img.seek(1)
                is_animated_gif = True
            except EOFError:
                pass
            finally:
                img.seek(0)

        # 6. Параноик: обрезаем большие изображения для борьбы со стеганографией
        stealth_trim = current_app.config.get('STEALTH_TRIM', True)
        if stealth_trim and (img.width > 2000 or img.height > 2000):
            img.thumbnail((2000, 2000), Image.LANCZOS)

        # 7. Генерация имени и расширения
        random_hex = secrets.token_hex(16)
        if webp_enabled and not is_animated_gif:
            # Конвертируем в WEBP
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGB")
            ext = ".webp"
            picture_fn = random_hex + ext
            picture_path = os.path.join(current_app.config['UPLOAD_FOLDER'], picture_fn)
            img.save(picture_path, format="WEBP", quality=85, method=6, save_all=False)
        else:
            # Сохраняем в исходном формате (или как есть для анимированного GIF)
            ext = os.path.splitext(f.filename)[1].lower()
            if ext == '.jpg':
                ext = '.jpeg'
            elif is_animated_gif:
                ext = '.gif'
            else:
                pass
            picture_fn = random_hex + ext
            picture_path = os.path.join(current_app.config['UPLOAD_FOLDER'], picture_fn)

            # Принудительная конвертация палитры, если нужно
            if img.mode in ('RGBA', 'P') and not is_animated_gif:
                img = img.convert('RGB')
            # Сохраняем с удалением EXIF
            save_kwargs = {'optimize': True, 'quality': 85}
            if not is_animated_gif:
                save_kwargs['exif'] = Image.Exif()
                img.save(picture_path, **save_kwargs)
            else:
                img.save(picture_path, save_all=True, loop=0, **save_kwargs)

        file_size = os.path.getsize(picture_path)

        # 8. Миниатюра
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
        except Exception as e:
            current_app.logger.warning(f"Thumbnail generation failed: {e}")
            thumb_fn = None

        # 9. SHA-256 хеш содержимого (для поиска дубликатов)
        f.stream.seek(0)
        file_data = f.read()
        sha256 = hashlib.sha256(file_data).hexdigest()

        saved.append((picture_fn, thumb_fn, idx, file_size, sha256))

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
