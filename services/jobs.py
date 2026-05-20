"""
Заглушка для очереди задач (воркеров).
В будущем здесь будет enqueue(job_type, payload), работающий через Redis/БД.
Пока просто логирует задание.
"""
import logging

logger = logging.getLogger(__name__)


def enqueue(job_type: str, payload: dict = None):
    """
    Поставить задачу в очередь.
    В будущем: отправка в Redis/PostgreSQL.
    """
    logger.info(f"Job enqueued: type={job_type}, payload={payload}")
    # TODO: реализовать реальную отправку
