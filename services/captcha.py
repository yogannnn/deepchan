import base64
import hashlib
import hmac
import random
import time

from captcha.image import ImageCaptcha
from flask import current_app


def generate_captcha():
    image = ImageCaptcha(width=280, height=90)

    captcha_text = "".join(random.choices("0123456789", k=6))

    image_data = image.generate(captcha_text).getvalue()

    image_base64 = base64.b64encode(image_data).decode("utf-8")

    timestamp = str(int(time.time()))

    payload = f"{captcha_text}:{timestamp}"

    signature = hmac.new(
        current_app.config["SECRET_KEY"].encode(), payload.encode(), hashlib.sha256
    ).hexdigest()

    token = f"{timestamp}:{signature}"

    return image_base64, captcha_text, token


def verify_captcha(answer, token, max_age=300):
    try:
        timestamp, signature = token.split(":", 1)

        if time.time() - int(timestamp) > max_age:
            return False

        answer = answer.strip()

        payload = f"{answer}:{timestamp}"

        expected_signature = hmac.new(
            current_app.config["SECRET_KEY"].encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)

    except Exception:
        return False
