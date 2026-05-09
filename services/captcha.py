import random
from captcha.image import ImageCaptcha


def generate_captcha():
    image = ImageCaptcha(width=280, height=90)
    captcha_text = "".join(random.choices("0123456789", k=6))
    data = image.generate(captcha_text)
    return data, captcha_text
