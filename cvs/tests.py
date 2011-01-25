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
        self.fakeIncoming('+BIRTH ALIMO MARY, F, HOME')
        self.fakeIncoming('+DEATH ADOCH,F,1DAY')
        self.fakeIncoming('+muac auma gloria,f,5months,yellow')
        self.fakeIncoming('+epi ma 12, bd 5')
        self.fakeIncoming('+home 12, wa 1, it 6')
        self.assertEquals(XFormSubmission.objects.count(), 5)
        self.assertEquals(PatientEncounter.objects.count(), 3)

    def testSimpleDocTest(self):
        """
            >>> print 'hi'
            hi        
        """
        pass
