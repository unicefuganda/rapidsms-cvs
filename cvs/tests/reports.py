'''
Created on Aug 16, 2011

@author: asseym
'''
from django.test import TestCase
from django.conf import settings
import datetime
import traceback
from rapidsms_httprouter.router import get_router, HttpRouterThread
from rapidsms_xforms.models import *
from rapidsms.messages.incoming import IncomingMessage, IncomingMessage
from rapidsms.models import Connection, Backend, Contact
from rapidsms_httprouter.models import Message
from rapidsms_httprouter.router import get_router
from django.contrib.auth.models import Group
from cvs.utils import init_xforms, monthly_reports
from healthmodels.models import *
from django.db import connection


class ModelTest(TestCase): #pragma: no cover

    def fake_incoming(self, message, connection=None):
        if connection is None:
            connection = self.connection
        router = get_router()
        return router.handle_incoming(connection.backend.name, connection.identity, message)


    def spoof_incoming_obj(self, message, connection=None):
        if connection is None:
            connection = Connection.objects.all()[0]
        incomingmessage = IncomingMessage(connection, message)
        incomingmessage.db_message = Message.objects.create(direction='I', connection=Connection.objects.all()[0], text=message)
        return incomingmessage

    def elapseTime(self, submission, seconds):
        newtime = submission.created - datetime.timedelta(seconds=seconds)
        cursor = connection.cursor()
        cursor.execute("update rapidsms_xforms_xformsubmission set created = '%s' where id = %d" %
                       (newtime.strftime('%Y-%m-%d %H:%M:%S.%f'), submission.pk))

    def setUp(self):
        if 'django.contrib.sites' in settings.INSTALLED_APPS:
            site_id = getattr(settings, 'SITE_ID', 1)
            Site.objects.get_or_create(pk=site_id, defaults={'domain':'rapidcvs.org'})
        for g in ['Village Health Team', 'OTC', 'ITC']:
            Group.objects.create(name=g)
        User.objects.get_or_create(username='admin')
        init_xforms()
        contact = Contact.objects.create(name='vht reporter')
        self.group = Group.objects.all()[0]
        contact.groups.add(self.group)
        contact.active = True
        contact.save()
        hp = HealthProvider.objects.create(pk=contact.pk, name='vht reporter')
        self.hp_group = hp.groups.add(self.group)
        hp.active = True
        hp.save()
        self.backend = Backend.objects.create(name='test')
        self.connection = Connection.objects.create(identity='8675309', backend=self.backend)
        self.connection.contact = contact
        self.connection.save()
        def test_run(self):
            return
        HttpRouterThread.run = test_run

    def testReport(self):
        self.fake_incoming('com 8, 3, 5, 6, 1, 7, 3')
        week = 7 * 86400
        self.elapseTime(XFormSubmission.objects.all()[0], week * 2)
        self.fake_incoming('com 6, 1, 5, 6, 1, 7, 3')
        self.elapseTime(XFormSubmission.objects.all().order_by('-created')[0], week)
        self.fake_incoming('com 1, 1, 2, 6, 1, 7, 3')
        monthly_reports()
        self.assertEquals(Message.objects.all().order_by('-date')[0].text, 'Last month you submitted 3 timely reports in 4 weeks: Thanks for your good work. Please remember to send your reports.')

    def testReportNoMessageInPreviousMonth(self):
        self.fake_incoming('com 8, 3, 5, 6, 1, 7, 3')
        week = 7 * 86400
        self.elapseTime(XFormSubmission.objects.all()[0], week * 5)
        monthly_reports()
        self.assertEquals(Message.objects.all().order_by('-date')[0].text, 'Last month you submitted 0 timely reports in 4 weeks: Your reports are important. Please make an effort to submit on time.')

    def testReportWithErrors(self):
        self.fake_incoming('com w, x, 5, 6, 1, 7, 3')
        week = 7 * 86400
        self.elapseTime(XFormSubmission.objects.all()[0], week * 2)
        self.fake_incoming('com 6, 1, 5, 6, 1, 7, 3')
        self.elapseTime(XFormSubmission.objects.all().order_by('-created')[0], week)
        self.fake_incoming('com 1, 1, 2, 6, 1, 7, 3')
        monthly_reports()
        self.assertEquals(Message.objects.all().order_by('-date')[0].text, 'Last month you submitted 2 timely reports in 4 weeks: Thanks for your effort. Please remember to submit on time.')
