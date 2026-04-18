import os
import secrets
import re
import time
import hashlib
import random
import io
from PIL import Image
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
    for idx, f in enumerate(files[:current_app.config.get('MAX_FILES', 4)]):
        if f.filename == '':
            continue
        random_hex = secrets.token_hex(8)
        _, f_ext = os.path.splitext(f.filename)
        picture_fn = random_hex + f_ext
        picture_path = os.path.join(current_app.config['UPLOAD_FOLDER'], picture_fn)

        f.stream.seek(0)
        file_data = f.read()
        md5 = hashlib.md5(file_data).hexdigest()
        file_size = len(file_data)

        f.stream.seek(0)
        i = Image.open(f.stream)
        if i.mode in ('RGBA', 'P'):
            i = i.convert('RGB')
        i.save(picture_path, optimize=True, quality=85)

        thumb_fn = random_hex + '_thumb' + f_ext
        thumb_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'thumbs', thumb_fn)
        i.thumbnail((200, 200))
        i.save(thumb_path)

        saved.append((picture_fn, thumb_fn, idx, file_size, md5))
    return saved

def parse_bbcode(text):
    # Жирный
    text = re.sub(r'\[b\](.*?)\[/b\]', r'<strong>\1</strong>', text, flags=re.IGNORECASE|re.DOTALL)
    # Курсив
    text = re.sub(r'\[i\](.*?)\[/i\]', r'<em>\1</em>', text, flags=re.IGNORECASE|re.DOTALL)
    # Подчёркнутый
    text = re.sub(r'\[u\](.*?)\[/u\]', r'<u>\1</u>', text, flags=re.IGNORECASE|re.DOTALL)
    # Зачёркнутый
    text = re.sub(r'\[s\](.*?)\[/s\]', r'<del>\1</del>', text, flags=re.IGNORECASE|re.DOTALL)
    # Спойлер
    text = re.sub(r'\[spoiler\](.*?)\[/spoiler\]', r'<details class="spoiler"><summary>Спойлер</summary>\1</details>', text, flags=re.IGNORECASE|re.DOTALL)
    # Код
    text = re.sub(r'\[code\](.*?)\[/code\]', r'<pre><code>\1</code></pre>', text, flags=re.IGNORECASE|re.DOTALL)
    return text

def process_urls(text):
    # Шаг 1: Сохраняем magnet-ссылки
    magnet_map = {}
    def magnet_saver(match):
        url = match.group(0)
        placeholder = f"__MAGNET_{len(magnet_map)}__"
        magnet_map[placeholder] = f'<a href="{url}" target="_blank" rel="noopener noreferrer">{url}</a>'
        return placeholder
    text = re.sub(r'magnet:\?[^\s<>"\']+', magnet_saver, text, flags=re.IGNORECASE)

    # Шаг 2: Обрабатываем остальные URL
    def url_replacer(match):
        url = match.group(0)
        if url.startswith('__MAGNET_'):
            return url
        if re.search(r'\.(i2p|onion)(/|$)', url, re.IGNORECASE):
            if not url.startswith('http://') and not url.startswith('https://'):
                url = 'http://' + url
            return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{match.group(0)}</a>'
        else:
            return f'{match.group(0)} <span class="clearnet-warning">[Alert! ClearNet]</span>'

    text = re.sub(r'''(?i)\b((?:https?://|ftp://)?[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:[a-z]{2,}|i2p|onion)(?:/[^\s<>"']*)?)\b''', url_replacer, text)

    # Шаг 3: Возвращаем magnet-ссылки
    for placeholder, link in magnet_map.items():
        text = text.replace(placeholder, link)
    return text

def process_comment(text, board_name, thread_id):
    # Сначала BB-коды
    text = parse_bbcode(text)
    # Затем цитирование
    def replace_quote(match):
        num = match.group(1)
        quoted_post = Post.query.filter_by(id=num, thread_id=thread_id).first()
        if quoted_post:
            quote_text = quoted_post.comment
            if len(quote_text) > 200:
                quote_text = quote_text[:200] + "..."
            return f'<blockquote class="inline-quote"><a href="{current_app.url_for("thread", board_name=board_name, thread_id=thread_id)}#post{num}">&gt;&gt;{num}</a> {quote_text}</blockquote>'
        return match.group(0)

    text = re.sub(r'>>(\d+)', replace_quote, text)
    # Затем ссылки
    text = process_urls(text)
    return text

def generate_captcha():
    from captcha.image import ImageCaptcha
    image = ImageCaptcha(width=280, height=90)
    captcha_text = ''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=5))
    data = image.generate(captcha_text)
    return data, captcha_text
