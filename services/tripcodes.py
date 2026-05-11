import base64
import hashlib
import hmac


def generate_tripcode(password, secret_key):
    """Возвращает защищённый трипкод (10 символов)."""
    if not password:
        return None
    signature = hmac.new(
        secret_key.encode(), password.encode(), hashlib.sha256
    ).digest()
    trip = base64.b64encode(signature, altchars=b"..").decode()[:10]
    return f"◆{trip}"
