from django.db import models
from rapidsms_xforms.models import XFormSubmission
from healthmodels.models.HealthProvider import HealthProvider
from rapidsms_httprouter.models import Message

class XFormFacilityReport(models.Model):
    """
    FIXME: Documentation
    """
    submission = models.ForeignKey(XFormSubmission, null=True, blank=True)
    reporter = models.ForeignKey(HealthProvider, null=True, blank=True)
    message = models.ForeignKey(Message, null=True, blank=True)
    valid = models.BooleanField(default=True)
    groups = models.ManyToManyField(Group, blank=True, null=True)
    
    class Meta:
        abstract = True