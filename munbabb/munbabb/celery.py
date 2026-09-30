import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'munbabb.settings')

app = Celery('munbabb')

app.config_from_object('django.conf:settings')

# setup priorities ( 0 Highest, 9 Lowest )
app.conf.broker_transport_options = {
    'priority_steps': list(range(10)),  # setup que to have 10 steps
    'queue_order_strategy': 'priority',  # setup que to use prio sorting
}
app.conf.task_default_priority = 5  # anything called with the task.delay() will be given normal priority (5)
app.conf.worker_prefetch_multiplier = 1  # only prefetch single tasks at a time on the workers so that prio tasks happen

app.conf.broker_connection_retry_on_startup = True

app.conf.ONCE = {
    'backend': 'celery_once.backends.Redis',
    'settings': {
        'url': 'redis://127.0.0.1:6379/0',
        'default_timeout': 60 * 60,
    }
}

app.autodiscover_tasks()

