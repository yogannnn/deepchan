import os
import secrets
import hashlib
import subprocess
import json
from PIL import Image, UnidentifiedImageError, ImageDraw, ImageFont
from flask import current_app, abort


def add_watermark(img, text, position=(5, 5)):
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16
        )
    except:
        font = ImageFont.load_default()
    draw.text((position[0] + 1, position[1] + 1), text, font=font, fill=(0, 0, 0))
    draw.text(position, text, font=font, fill=(255, 255, 255))
    return img


def get_media_duration(filepath):
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                filepath,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            return float(data["format"]["duration"])
    except Exception:
        pass
    return None


def generate_video_thumbnail(video_path, thumb_path, width=200):
    try:
        tmp_thumb = thumb_path + ".tmp.webp"
        subprocess.run(
            [
                "ffmpeg",
                "-i",
                video_path,
                "-ss",
                "00:00:01",
                "-vframes",
                "1",
                "-vf",
                f"scale={width}:-1",
                "-y",
                tmp_thumb,
            ],
            capture_output=True,
            timeout=15,
            check=True,
        )
        img = Image.open(tmp_thumb)
        img = add_watermark(img, "video")
        img.save(thumb_path, format="WEBP", quality=80)
        os.remove(tmp_thumb)
        return True
    except Exception:
        return False


def clean_media_metadata(input_path, output_path, is_audio=False):
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-i",
                input_path,
                "-map_metadata",
                "-1",
                "-c",
                "copy",
                "-y",
                output_path,
            ],
            capture_output=True,
            timeout=30,
            check=True,
        )
        return True
    except Exception:
        return False


def generate_audio_thumbnail(text="AUDIO", width=200, height=200):
    img = Image.new("RGB", (width, height), color="#0d140d")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24
        )
    except:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    draw.text((x + 1, y + 1), text, font=font, fill=(0, 0, 0))
    draw.text((x, y), text, font=font, fill=(255, 255, 255))
    return img


def save_files(files):
    saved = []
    if not files:
        return saved
    max_files = int(current_app.config["SETTINGS"].max_files)
    if len(files) > max_files:
        abort(400, description=f"Слишком много файлов (максимум {max_files})")
    max_image_dimension = current_app.config["SETTINGS"].max_image_dimension
    max_video_duration = current_app.config["SETTINGS"].max_video_duration
    max_video_size = current_app.config["SETTINGS"].max_video_size
    max_audio_duration = current_app.config["SETTINGS"].max_audio_duration
    max_audio_size = current_app.config["SETTINGS"].max_audio_size
    webp_enabled = current_app.config["SETTINGS"].webp_convert_enabled
    stealth_trim = current_app.config["SETTINGS"].stealth_trim
    allowed_extensions = current_app.config["SETTINGS"].allowed_extensions
    video_exts = {"mp4", "webm", "mov", "avi", "mkv"}
    audio_exts = {"mp3", "ogg", "flac", "wav", "m4a"}
    for idx, f in enumerate(files):
        if f.filename == "":
            continue
        ext = os.path.splitext(f.filename)[1].lower().lstrip(".")
        if ext not in allowed_extensions:
            abort(400, description=f"Недопустимый формат: {ext}")
        f.stream.seek(0, os.SEEK_END)
        file_size = f.tell()
        f.stream.seek(0)
        is_video = ext in video_exts
        is_audio = ext in audio_exts
        if is_video:
            if file_size > max_video_size:
                abort(
                    400,
                    description=f"Видео слишком большое (макс {max_video_size//1024//1024} МБ)",
                )
            video_tmp = os.path.join(
                current_app.config["UPLOAD_FOLDER"], secrets.token_hex(16) + "." + ext
            )
            f.save(video_tmp)
            duration = get_media_duration(video_tmp)
            if duration is None or duration > max_video_duration:
                os.remove(video_tmp)
                abort(
                    400,
                    description=f"Видео слишком длинное (макс {max_video_duration} сек)",
                )
            random_hex = secrets.token_hex(16)
            picture_fn = random_hex + "." + ext
            picture_path = os.path.join(current_app.config["UPLOAD_FOLDER"], picture_fn)
            if not clean_media_metadata(video_tmp, picture_path):
                os.remove(video_tmp)
                abort(400, description="Ошибка обработки видео")
            os.remove(video_tmp)
            thumb_fn = random_hex + "_thumb.webp"
            thumb_path = os.path.join(
                current_app.config["UPLOAD_FOLDER"], "thumbs", thumb_fn
            )
            if not generate_video_thumbnail(picture_path, thumb_path):
                thumb_fn = None
                thumb_path = None
            f.stream.seek(0)
            file_data = f.read()
            sha256 = hashlib.sha256(file_data).hexdigest()
            saved.append(
                (picture_fn, thumb_fn, idx, file_size, sha256, "video", duration)
            )
        elif is_audio:
            if file_size > max_audio_size:
                abort(
                    400,
                    description=f"Аудио слишком большое (макс {max_audio_size//1024//1024} МБ)",
                )
            audio_tmp = os.path.join(
                current_app.config["UPLOAD_FOLDER"], secrets.token_hex(16) + "." + ext
            )
            f.save(audio_tmp)
            duration = get_media_duration(audio_tmp)
            if duration is None or duration > max_audio_duration:
                os.remove(audio_tmp)
                abort(
                    400,
                    description=f"Аудио слишком длинное (макс {max_audio_duration} сек)",
                )
            random_hex = secrets.token_hex(16)
            picture_fn = random_hex + "." + ext
            picture_path = os.path.join(current_app.config["UPLOAD_FOLDER"], picture_fn)
            if not clean_media_metadata(audio_tmp, picture_path, is_audio=True):
                os.remove(audio_tmp)
                abort(400, description="Ошибка обработки аудио")
            os.remove(audio_tmp)
            thumb_fn = random_hex + "_thumb.webp"
            thumb_path = os.path.join(
                current_app.config["UPLOAD_FOLDER"], "thumbs", thumb_fn
            )
            try:
                thumb_img = generate_audio_thumbnail()
                thumb_img.save(thumb_path, format="WEBP", quality=80)
            except Exception:
                thumb_fn = None
            f.stream.seek(0)
            file_data = f.read()
            sha256 = hashlib.sha256(file_data).hexdigest()
            saved.append(
                (picture_fn, thumb_fn, idx, file_size, sha256, "audio", duration)
            )
        else:
            try:
                f.stream.seek(0)
                img = Image.open(f.stream)
                img.verify()
            except (UnidentifiedImageError, Exception) as e:
                abort(400, description=f"Некорректный файл изображения: {str(e)}")
            f.stream.seek(0)
            img = Image.open(f.stream)
            if img.width > max_image_dimension or img.height > max_image_dimension:
                abort(
                    400,
                    description=f"Разрешение превышает {max_image_dimension}x{max_image_dimension}",
                )
            is_animated_gif = False
            if img.format == "GIF":
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
                picture_path = os.path.join(
                    current_app.config["UPLOAD_FOLDER"], picture_fn
                )
                img.save(
                    picture_path, format="WEBP", quality=85, method=6, save_all=False
                )
            else:
                ext = os.path.splitext(f.filename)[1].lower()
                if ext == ".jpg":
                    ext = ".jpeg"
                elif is_animated_gif:
                    ext = ".gif"
                picture_fn = random_hex + ext
                picture_path = os.path.join(
                    current_app.config["UPLOAD_FOLDER"], picture_fn
                )
                if img.mode in ("RGBA", "P") and not is_animated_gif:
                    img = img.convert("RGB")
                save_kwargs = {"optimize": True, "quality": 85}
                if not is_animated_gif:
                    save_kwargs["exif"] = Image.Exif()
                    img.save(picture_path, **save_kwargs)
                else:
                    img.save(picture_path, save_all=True, loop=0, **save_kwargs)
            file_size = os.path.getsize(picture_path)
            thumb_fn = (
                random_hex
                + "_thumb"
                + (".webp" if webp_enabled and not is_animated_gif else ext)
            )
            thumb_path = os.path.join(
                current_app.config["UPLOAD_FOLDER"], "thumbs", thumb_fn
            )
            try:
                thumb_img = Image.open(picture_path)
                if thumb_img.mode not in ("RGB", "RGBA"):
                    thumb_img = thumb_img.convert("RGB")
                thumb_img.thumbnail((200, 200))
                thumb_img = add_watermark(thumb_img, "img")
                if webp_enabled:
                    thumb_img.save(thumb_path, format="WEBP", quality=80, method=6)
                else:
                    thumb_img.save(thumb_path, optimize=True, quality=80)
            except Exception:
                thumb_fn = None
            f.stream.seek(0)
            file_data = f.read()
            sha256 = hashlib.sha256(file_data).hexdigest()
            saved.append((picture_fn, thumb_fn, idx, file_size, sha256, "image", None))
    return saved
