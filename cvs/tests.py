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
            return submission
        return None

    def testBasicSubmission(self):
        self.fakeIncoming('+BIRTH Terra Weikel, F, HOME')
        self.fakeIncoming('+DEATH Malthe Borch, M,1DAY')
        self.fakeIncoming('+muac Matt Berg, M,5months,yellow')
        self.fakeIncoming('+epi ma 12, bd 5')
        self.fakeIncoming('+home 12, wa 1, it 6')
        self.assertEquals(XFormSubmission.objects.count(), 5)
        self.assertEquals(PatientEncounter.objects.count(), 3)

    def testBirth(self):
        s = self.fakeIncoming('+birth David McCann, M, Facility')
        # test submission parsing
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
        s = self.fakeIncoming('+birth terra weikel, F, Home')
        self.assertEquals(s.eav.birth_place, 'HOME')
        self.assertEquals(s.eav.birth_gender, 'F')

    def testDeath(self):
        s = self.fakeIncoming('+DEATH maltheSMS, M, 2Y')
        self.assertEquals(s.eav.death_name, 'maltheSMS')
        self.assertEquals(s.eav.death_gender, 'M')
        self.assertEquals(s.eav.death_age, 730)
        self.assertEquals(PatientEncounter.objects.filter(submission=s).count(), 1)
        pe = PatientEncounter.objects.get(submission=s)
        p = pe.patient
        self.assertEquals(p.first_name, 'maltheSMS')
        self.failUnless(p.age.days == 730)
        s = self.fakeIncoming('+death maltheCVS, F, 1d')
        self.assertEquals(s.eav.death_gender, 'F')

    def testMuac(self):
        s = self.fakeIncoming('+muac Sean Blaschke, M,5months,yellow')
        self.assertEquals(s.eav.muac_name, 'Sean Blaschke')
        self.assertEquals(s.eav.muac_gender, 'M')
        self.assertEquals(s.eav.muac_age, 150)
        self.assertEquals(s.eav.muac_category, 'Y')
        self.assertEquals(s.eav.muac_ignored, 'F')
        pe = PatientEncounter.objects.get(submission=s)
        p = pe.patient
        self.assertEquals(p.first_name, 'Sean')
        self.assertEquals(p.last_name, 'Blaschke')
        self.failUnless(p.age.days == 150)
        s = self.fakeIncoming('+muac Terra Weikel, F,5months,red')
        self.assertEquals(s.eav.muac_category, 'R')
        self.assertEquals(s.eav.muac_gender, 'F')
        s = self.fakeIncoming('+muac Alexis Coppola, F, 5months, green, oedema')
        self.assertEquals(s.eav.muac_category, 'G')
        self.assertEquals(s.eav.muac_ignored, 'T')

    def testEpi(self):
        s = self.fakeIncoming('+epi bd 5,ma 12,tb 1,ab 2,af 3,mg 4,me 5, ch 6, gw 7, nt 8, yf 9, pl 10, ra 11, vf 12, ei 13')
        self.assertEquals(s.eav.epi_bd, 5)
        self.assertEquals(s.eav.epi_ma, 12)
        self.assertEquals(s.eav.epi_tb, 1)
        self.assertEquals(s.eav.epi_ab, 2)
        self.assertEquals(s.eav.epi_af, 3)
        self.assertEquals(s.eav.epi_mg, 4)
        self.assertEquals(s.eav.epi_me, 5)
        self.assertEquals(s.eav.epi_ch, 6)
        self.assertEquals(s.eav.epi_gw, 7)
        self.assertEquals(s.eav.epi_nt, 8)
        self.assertEquals(s.eav.epi_yf, 9)
        self.assertEquals(s.eav.epi_pl, 10)
        self.assertEquals(s.eav.epi_ra, 11)
        self.assertEquals(s.eav.epi_vf, 12)
        self.assertEquals(s.eav.epi_ei, 13)

    def testHome(self):
        s = self.fakeIncoming('+home 13, wa 9, it 10, la 11, ha 12')
        self.assertEquals(s.eav.home_wa, 9)
        self.assertEquals(s.eav.home_it, 10)
        self.assertEquals(s.eav.home_la, 11)
        self.assertEquals(s.eav.home_ha, 12)
        self.assertEquals(s.eav.home_to, 13)

    def testSimpleDocTest(self):
        """
            >>> print 'hi'
            hi        
        """
        pass
