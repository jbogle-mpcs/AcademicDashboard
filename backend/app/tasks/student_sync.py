# TODO: implement
from app.celery import celery


@celery.task(name="tasks.assessment_sync")
def sync_assessments():
    """Scan import directories and ingest assessment files. TODO: implement."""
    raise NotImplementedError("assessment_sync is not yet implemented")