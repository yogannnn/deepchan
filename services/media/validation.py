"""
Валидация медиафайлов: расширения, размеры, MIME.
"""
from core.exceptions import MediaValidationError


def validate_extension(ext, allowed_extensions):
    if ext not in allowed_extensions:
        raise MediaValidationError(f"Недопустимый формат: {ext}")


def validate_file_size(file_size, max_size, file_type="файл"):
    if file_size > max_size:
        max_mb = max_size // (1024 * 1024)
        raise MediaValidationError(f"{file_type} слишком большое (макс {max_mb} МБ)")


def validate_image_resolution(img, max_dimension):
    if img.width > max_dimension or img.height > max_dimension:
        raise MediaValidationError(
            f"Разрешение превышает {max_dimension}x{max_dimension}"
        )
