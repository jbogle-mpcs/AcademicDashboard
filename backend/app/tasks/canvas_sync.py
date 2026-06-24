from app.celery import celery
from app.services.canvas import CanvasSyncService


@celery.task(name="tasks.canvas_sync")
def sync_canvas():
    service = CanvasSyncService()

    return service.run()