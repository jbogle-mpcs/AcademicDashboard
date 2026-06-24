from celery import Celery
from app.core.config import settings

celery = Celery(
    "assessment",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery.conf.update(
    # Prevent RCE via pickle — only accept JSON-serialised tasks
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Timezone
    timezone="UTC",
    enable_utc=True,
    # Automatically discover tasks in app/tasks/
    imports=[
        "app.tasks.canvas_sync",
        "app.tasks.student_sync",
        "app.tasks.assessment_sync",
    ],
)