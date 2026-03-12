from celery import Celery

from app.core.config import settings


celery = Celery('scrapi', broker=settings.redis_url, backend=settings.redis_url)
celery.conf.task_track_started = True
celery.conf.task_serializer = 'json'
celery.conf.result_serializer = 'json'
celery.conf.beat_schedule = {
    'dispatch-schedules-every-minute': {
        'task': 'schedules.dispatch',
        'schedule': 60.0,
    }
}
