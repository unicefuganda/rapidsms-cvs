"""
Basic tests for CVS
"""

from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.test.client import Client
from django.core.exceptions import ValidationError
from eav.models import Attribute
from django.contrib.sites.models import Site
from rapidsms.messages.incoming import IncomingMessage
from rapidsms_xforms.models import *
from cvs.utils import init_xforms
from healthmodels.models import *
from rapidsms.models import Contact, Connection, Backend
from rapidsms_xforms.app import App
from rapidsms.messages.incoming import IncomingMessage
from rapidsms_httprouter.models import Message

class ModelTest(TestCase): #pragma: no cover

    def setUp(self):
        User.objects.create_user('admin', 'test@doesntmatter.com', 'password')
        init_xforms()
        hp = HealthProvider.objects.create(name='David McCann')
        b = Backend.objects.create(name='test')
        c = Connection.objects.create(identity='8675309', backend=b)
        c.contact = hp
        c.save()
#        self.user = User.objects.create_user('fred', 'fred@wilma.com', 'secret')
#        self.user.save()    

    def fakeIncoming(self, message):
        form = XForm.find_form(message)

        # if so, process it
        incomingmessage = IncomingMessage(Connection.objects.all()[0], message)
        incomingmessage.db_message = Message.objects.create(direction='I', connection=Connection.objects.all()[0], text=message)
        if form:
            submission = form.process_sms_submission(incomingmessage)

    def testBasicSubmission(self):
        self.fakeIncoming('+BIRTH Terra Weikel, F, HOME')
        self.fakeIncoming('+DEATH Malthe Borch, M,1DAY')
        self.fakeIncoming('+muac Sean Blaschke, M,5months,yellow')
        self.fakeIncoming('+epi ma 12, bd 5')
        self.fakeIncoming('+home 12, wa 1, it 6')
        self.assertEquals(XFormSubmission.objects.count(), 5)
        self.assertEquals(PatientEncounter.objects.count(), 3)

    def testBirth(self):
        self.fakeIncoming('+birth David McCann, M, Facility')
        # test submission parsing
        s = XFormSubmission.objects.all()[0]
        self.assertEquals(s.eav.birth_place, 'FACILITY')
        self.assertEquals(s.eav.birth_name, 'David McCann')
        self.assertEquals(s.eav.birth_gender, 'M')
        self.assertEquals(PatientEncounter.objects.filter(submission=s).count(), 1)
        pe = PatientEncounter.objects.get(submission=s)
        p = pe.patient
        # test patient creation
        self.assertEquals(p.first_name, 'David')
        self.assertEquals(p.last_name, 'McCann')
        self.failUnless(p.age.days < 1)
        self.fakeIncoming('+birth terra weikel, F, Home')
        self.assertEquals(XFormSubmission.objects.order_by('-pk')[0].eav.birth_place, 'HOME')
        self.assertEquals(XFormSubmission.objects.order_by('-pk')[0].eav.birth_gender, 'F')



    def testSimpleDocTest(self):
        """
            >>> print 'hi'
            hi        
        """
        pass
