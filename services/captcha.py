import random
import time
import hmac
import hashlib
import base64
from captcha.image import ImageCaptcha
from flask import current_app


def generate_captcha():
    """Генерирует капчу и возвращает (data_base64, text, token)."""
    image = ImageCaptcha(width=280, height=90)
    captcha_text = "".join(random.choices("0123456789", k=6))
    data = image.generate(captcha_text).getvalue()
    image_base64 = base64.b64encode(data).decode()
    timestamp = int(time.time())
    secret = current_app.config["SECRET_KEY"]
    payload = f"{captcha_text}:{timestamp}"
    signature = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    token = f"{timestamp}:{signature}"
    return image_base64, captcha_text, token


def verify_captcha(answer, token, max_age=300):
    """Проверяет ответ капчи по токену (stateless)."""
    try:
        timestamp, signature = token.split(":", 1)
        if time.time() - int(timestamp) > max_age:
            return False
        secret = current_app.config["SECRET_KEY"]
        answer = answer.strip()
        payload = f"{answer}:{timestamp}"
        expected_signature = hmac.new(
            secret.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(signature, expected_signature)
    except Exception:
        return False
