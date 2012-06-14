from django.conf import settings
from celery.task import Task, task
from celery.registry import tasks
from dhis2.utils import send_data, postXmlForSubmission

@task
def sendSubmissionToDHIS2(submission,facility_code,week):
    postXml = postXmlForSubmission(submission, facility_code, week)
    try:
        resp = send_data(postXml)
    except:
        pass

