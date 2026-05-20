"""Доменные исключения DeepChan."""


class DeepChanError(Exception):
    """Базовое исключение."""

    status_code = 400


class ThreadLockedError(DeepChanError):
    status_code = 403


class BannedError(DeepChanError):
    status_code = 403


class CaptchaError(DeepChanError):
    status_code = 400


class RateLimitError(DeepChanError):
    status_code = 429


class ValidationError(DeepChanError):
    status_code = 400


class MediaValidationError(ValidationError):
    pass
