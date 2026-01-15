import os
from celery import Celery
from celery.schedules import crontab

# Django ayarlarını varsayılan olarak ayarla
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sarscope_project.settings')

app = Celery('sarscope_project')

# Ayarları settings.py'dan al (CELERY_ ile başlayanlar)
# namespace='CELERY' demek settings.py içinde CELERY_BROKER_URL gibi ayarları arar.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Tüm uygulamalardaki tasks.py dosyalarını otomatik bul
app.autodiscover_tasks()

# Zamanlanmış Görevler (Celery Beat)
app.conf.beat_schedule = {
    'saat-basi-fiyat-taramasi': {
        'task': 'core.tasks.scan_all_products_task',
        'schedule': crontab(minute=0),  # Her saat başı (Örn: 13:00, 14:00...)
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')