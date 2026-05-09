from services.media import (
    save_files,
    add_watermark,
    get_media_duration,
    generate_video_thumbnail,
    clean_media_metadata,
    generate_audio_thumbnail,
)
import base64
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
from services.captcha import generate_captcha
from services.csrf import generate_csrf_token, verify_csrf_token
from PIL import Image, UnidentifiedImageError, ImageDraw, ImageFont
from flask import current_app, request, abort
from models import Post

_last_post_time = {}


def check_rate_limit():
    ip = request.remote_addr
    now = time.time()
    if ip in _last_post_time:
        elapsed = now - _last_post_time[ip]
        limit = int(current_app.config.get("RATE_LIMIT_SECONDS", 30))
        if elapsed < limit:
            abort(
                429, description=f"Слишком часто. Подождите {limit - int(elapsed)} сек."
            )
    _last_post_time[ip] = now


def check_ban(ip):
    from models import Ban
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    ban = Ban.query.filter(
        Ban.ip_pattern == ip,
        Ban.active == True,
        (Ban.expires_at == None) | (Ban.expires_at > now),
    ).first()
    if ban:
        abort(403, description=f"Вы забанены. Причина: {ban.reason or 'не указана'}")


def apply_word_filters(text):
    from models import WordFilter

    filters = WordFilter.query.filter_by(active=True).all()
    for f in filters:
        if f.is_regex:
            if re.search(f.pattern, text, re.IGNORECASE):
                if f.action == "block":
                    abort(
                        400,
                        description=f"Сообщение содержит запрещённое выражение: {f.pattern}",
                    )
                elif f.action == "replace":
                    text = re.sub(f.pattern, f.replacement, text, flags=re.IGNORECASE)
        else:
            if f.pattern.lower() in text.lower():
                if f.action == "block":
                    abort(
                        400,
                        description=f"Сообщение содержит запрещённое слово: {f.pattern}",
                    )
                elif f.action == "replace":
                    text = text.replace(f.pattern, f.replacement)
    return text


def parse_bbcode(text):
    text = re.sub(
        r"\[b\](.*?)\[/b\]",
        r"<strong>\1</strong>",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    text = re.sub(
        r"\[i\](.*?)\[/i\]", r"<em>\1</em>", text, flags=re.IGNORECASE | re.DOTALL
    )
    text = re.sub(
        r"\[u\](.*?)\[/u\]", r"<u>\1</u>", text, flags=re.IGNORECASE | re.DOTALL
    )
    text = re.sub(
        r"\[s\](.*?)\[/s\]", r"<del>\1</del>", text, flags=re.IGNORECASE | re.DOTALL
    )
    text = re.sub(
        r"\[spoiler\](.*?)\[/spoiler\]",
        r'<details class="spoiler"><summary>Спойлер</summary>\1</details>',
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    text = re.sub(
        r"\[code\](.*?)\[/code\]",
        r"<pre><code>\1</code></pre>",
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    return text


def process_urls(text):
    def magnet_replace(match):
        url = match.group(0)
        return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{url}</a>'

    text = re.sub(r'magnet:\?[^\s<>"\']+', magnet_replace, text, flags=re.IGNORECASE)

    def url_replace(match):
        url = match.group(0)
        if re.search(
            r"^(https?://)?(127\.0\.0\.1|\[::1\]|::1)([/:]|$)", url, re.IGNORECASE
        ):
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "http://" + url
            return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{match.group(0)}</a>'
        if re.search(r"\.(i2p|onion)(/|$)", url, re.IGNORECASE):
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "http://" + url
            return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{match.group(0)}</a>'
        return f'{match.group(0)}<span class="clearnet-warning">ClearNet</span>'

    text = re.sub(
        r"""(?i)\b((?:https?://|ftp://)?[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:[a-z]{2,}|i2p|onion)(?:/[^\s<>"']*)?)\b""",
        url_replace,
        text,
    )
    text = re.sub(
        r"""(?i)\b((?:https?://|ftp://)?(?:[0-9]{1,3}\.){3}[0-9]{1,3})(?::[0-9]+)?(?:/[^\s<>"']*)?\b""",
        url_replace,
        text,
    )
    return text


def process_comment(text, board_name, thread_id):
    text = html.escape(text)
    text = text.replace("&gt;&gt;", ">>")
    text = text.replace("&#91;", "[").replace("&#93;", "]")

    def replace_quote(match):
        num = match.group(1)
        quoted_post = Post.query.filter_by(id=num, thread_id=thread_id).first()
        if quoted_post:
            quote_text = html.escape(quoted_post.comment)
            if len(quote_text) > 200:
                quote_text = quote_text[:200] + "..."
            return f'<blockquote class="inline-quote"><a href="{current_app.url_for("board.thread", board_name=board_name, thread_id=thread_id)}#post{num}">&gt;&gt;{num}</a> {quote_text}</blockquote>'
        return match.group(0)

    text = re.sub(r">>(\d+)", replace_quote, text)
    text = parse_bbcode(text)
    text = process_urls(text)
    return text


# ===== Утилиты для радио =====
def get_file_hash(filepath):
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def convert_for_radio(input_path, output_path, artist=None, title=None, bitrate="128k"):
    tmp_path = output_path + ".tmp.mp3"
    cmd = [
        "/usr/bin/ffmpeg",
        "-i",
        input_path,
        "-b:a",
        bitrate,
        "-map_metadata",
        "-1",
        "-y",
        tmp_path,
    ]
    subprocess.run(cmd, capture_output=True, timeout=60, check=True)
    if artist or title:
        cmd2 = ["/usr/bin/ffmpeg", "-i", tmp_path, "-c", "copy"]
        if artist:
            cmd2 += ["-metadata", f"artist={artist}"]
        if title:
            cmd2 += ["-metadata", f"title={title}"]
        cmd2 += ["-y", output_path]
        subprocess.run(cmd2, capture_output=True, timeout=30, check=True)
        os.remove(tmp_path)
    else:
        os.rename(tmp_path, output_path)
    return True


def update_icecast_playlist(playlist_file, tracks):
    import os

    radio_folder = current_app.config.get("RADIO_FOLDER", "/root/deepchan/static/radio")
    with open(playlist_file, "w") as f:
        for track in tracks:
            if track.file_path and os.path.exists(track.file_path):
                rel_path = os.path.relpath(track.file_path, radio_folder)
                f.write(rel_path + "\n")
    # Перезагружаем Icecast
    import subprocess

    subprocess.run(["/opt/deepchan/radio_control.sh", "reload"], capture_output=True)


def is_icecast_running():
    import subprocess

    result = subprocess.run(["pgrep", "-f", "icecast2"], capture_output=True)
    return result.returncode == 0


import base64


def generate_tripcode(password, secret_key):
    """Возвращает защищённый трипкод (10 символов)."""
    if not password:
        return None
    signature = hmac.new(
        secret_key.encode(), password.encode(), hashlib.sha256
    ).digest()
    trip = base64.b64encode(signature, altchars=b"..").decode()[:10]
    return f"◆{trip}"
