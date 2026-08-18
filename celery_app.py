from celery import Celery

from settings import settings

celery_app = Celery(
    'celery_fakturo',
    broker = f'redis://{settings.redis_host}:{settings.redis_port}/1',
    backend= f'redis://{settings.redis_host}:{settings.redis_port}/2'
)