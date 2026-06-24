from app.celery import celery
from app.services.assessments import AssessmentImporter


@celery.task(name="tasks.assessment_sync")
def sync_assessments():
    importer = AssessmentImporter()

    return importer.run()