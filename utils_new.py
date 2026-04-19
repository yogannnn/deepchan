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
from PIL import Image, UnidentifiedImageError, ImageDraw, ImageFont
from flask import current_app, request, abort
from models import Post

_last_post_time = {}

# ... (все остальные функции без изменений до save_files)

def add_watermark(img, text, position=(5, 5)):
    """Добавляет белый текст с чёрной тенью в левый верхний угол."""
    draw = ImageDraw.Draw(img)
    # Пытаемся загрузить шрифт, если нет — стандартный
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
    except:
        font = ImageFont.load_default()
    # Тень
    draw.text((position[0]+1, position[1]+1), text, font=font, fill=(0,0,0))
    # Основной текст
    draw.text(position, text, font=font, fill=(255,255,255))
    return img

def generate_video_thumbnail(video_path, thumb_path, width=200):
    """Извлекает кадр из видео, сохраняет как WEBP и добавляет водяной знак 'video'."""
    try:
        # Сначала создаём временный файл без водяного знака
        tmp_thumb = thumb_path + ".tmp.webp"
        subprocess.run(
            ['ffmpeg', '-i', video_path, '-ss', '00:00:01', '-vframes', '1',
             '-vf', f'scale={width}:-1', '-y', tmp_thumb],
            capture_output=True, timeout=15, check=True
        )
        # Открываем, добавляем водяной знак и сохраняем в целевой файл
        img = Image.open(tmp_thumb)
        img = add_watermark(img, "video")
        img.save(thumb_path, format="WEBP", quality=80)
        os.remove(tmp_thumb)
        return True
    except Exception:
        return False

# Внутри save_files, в блоке обработки изображений, при создании миниатюры:
# ... (после создания thumb_img) ...
# thumb_img = add_watermark(thumb_img, "img")
# thumb_img.save(...)

# Приведём соответствующий фрагмент из save_files (вставим add_watermark)
