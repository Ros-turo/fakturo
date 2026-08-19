from celery import Celery
from random import random
from settings import settings

celery_app = Celery(
    'celery_fakturo',
    broker = f'redis://{settings.redis_host}:{settings.redis_port}/1',
    backend= f'redis://{settings.redis_host}:{settings.redis_port}/2'
)

@celery_app.task(autoretry_for=(ConnectionError,), max_retries=3, retry_backoff=True)
def send_email_task(email: str, text:str ):
    if random() < 0.7:
        print(email, text)
    else:
        raise ConnectionError()