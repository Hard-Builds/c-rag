from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "c-rag-worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.worker.tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_conetnt=["json"],
    timezone="UTC",
    worker_pool="celery_aio_pool.pool:AsyncIOPool"
)
