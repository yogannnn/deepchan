import hashlib
import hmac
import time


def generate_csrf_token(user_id, action, secret_key, timestamp=None):
    if timestamp is None:
        timestamp = int(time.time())
    message = f"{user_id}:{action}:{timestamp}"
    token = hmac.new(secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()
    return token, timestamp


def verify_csrf_token(user_id, action, token, timestamp, secret_key, max_age=600):
    if int(time.time()) - int(timestamp) > max_age:
        return False
    expected_token, _ = generate_csrf_token(user_id, action, secret_key, timestamp)
    return hmac.compare_digest(expected_token, token)
