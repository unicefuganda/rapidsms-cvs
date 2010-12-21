from django.db import models
from rapidsms.models import Contact
from rapidsms_xforms.models import XFormSubmission
from healthmodels.models.HealthProvider import HealthProvider
from rapidsms_httprouter.models import Message

class XFormPatientEncounter(models.Model):
    """
    FIXME: Documentation
    """
    submission = models.OneToOneField(XFormSubmission, null=True, blank=True, related_name='report')
    reporter = models.ForeignKey(HealthProvider, null=True, blank=True)
    message = models.ForeignKey(Message, null=True, blank=True)
    valid = models.BooleanField(default=True)

    class Meta:
        abstract = True