"""
Basic tests for CVS
"""

from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User, Group
from django.test.client import Client
from django.core.exceptions import ValidationError
from eav.models import Attribute
from django.contrib.sites.models import Site
from rapidsms.messages.incoming import IncomingMessage
from rapidsms.models import Contact
from rapidsms_xforms.models import *
from cvs.utils import init_xforms
from healthmodels.models import *
from rapidsms.models import Contact, Connection, Backend
from rapidsms_xforms.app import App
from rapidsms_httprouter.models import Message
from rapidsms.contrib.locations.models import Location
from cvs.tests.util import fake_incoming
import datetime

class ModelTest(TestCase): #pragma: no cover

    def setUp(self):
        try:
            User.objects.get(username='admin')
        except User.DoesNotExist:
            User.objects.create_user('admin', 'test@doesntmatter.com', 'password')
        init_xforms()
        hp = HealthProvider.objects.create(name='David McCann')
        b = Backend.objects.create(name='test')
        c = Connection.objects.create(identity='8675309', backend=b)
        c.contact = hp
        c.save()
        Group.objects.create(name='Peer Village Health Team')
        Group.objects.create(name='Village Health Team')
#        self.user = User.objects.create_user('fred', 'fred@wilma.com', 'secret')
#        self.user.save()    

    def fakeErrorMessage(self, message, connection=None):
        form = XForm.find_form(message)

        if connection is None:
            connection = Connection.objects.all()[0]
        # if so, process it
        incomingmessage = IncomingMessage(connection, message)
        incomingmessage.db_message = Message.objects.create(direction='I', connection=Connection.objects.all()[0], text=message)
        if form:
            submission = form.process_sms_submission(incomingmessage)
            self.failUnless(submission.has_errors)
        return

    def incomingResponse(self, message, expected_response, connection=None):
        s = fake_incoming(message, connection)
        self.assertEquals(s.response, expected_response)

    def testBasicSubmission(self):
        fake_incoming('+BIRTH Terra Weikel, F, HOME')
        fake_incoming('+DEATH Malthe Borch, M,1DAY')
        fake_incoming('+muac Matt Berg, M,5months,yellow')
        fake_incoming('+epi ma 12, bd 5')
        fake_incoming('+home 12, wa 1, it 6')
        self.assertEquals(XFormSubmission.objects.count(), 5)
        self.assertEquals(PatientEncounter.objects.count(), 3)

    def testBirth(self):
        s = fake_incoming('+birth David McCann, M, Facility')
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
        self.failUnless(p.age.days <= 1)
        s = fake_incoming('+birth terra weikel, F, Home')
        self.assertEquals(s.eav.birth_place, 'HOME')
        self.assertEquals(s.eav.birth_gender, 'F')

    def testDeath(self):
        s = fake_incoming('+DEATH maltheSMS, M, 2Y')
        self.assertEquals(s.eav.death_name, 'maltheSMS')
        self.assertEquals(s.eav.death_gender, 'M')
        self.failUnless(s.eav.death_age - 730 < 2)
        self.assertEquals(PatientEncounter.objects.filter(submission=s).count(), 1)
        pe = PatientEncounter.objects.get(submission=s)
        p = pe.patient
        self.assertEquals(p.first_name, 'maltheSMS')
        self.failUnless(p.age.days - 730 < 2)
        s = fake_incoming('+death maltheCVS, F, 1d')
        self.assertEquals(s.eav.death_gender, 'F')

    def testMuac(self):
        s = fake_incoming('+muac Sean Blaschke, M,5months,yellow')
        self.assertEquals(s.eav.muac_name, 'Sean Blaschke')
        self.assertEquals(s.eav.muac_gender, 'M')
        self.failUnless(s.eav.muac_age - 150 < 2)
        self.assertEquals(s.eav.muac_category, 'Y')
        self.assertEquals(s.eav.muac_ignored, 'F')
        pe = PatientEncounter.objects.get(submission=s)
        p = pe.patient
        self.assertEquals(p.first_name, 'Sean')
        self.assertEquals(p.last_name, 'Blaschke')
        self.failUnless(p.age.days - 150 < 2)
        s = fake_incoming('+muac Terra Weikel, F,5months,red')
        self.assertEquals(s.eav.muac_category, 'R')
        self.assertEquals(s.eav.muac_gender, 'F')
        s = fake_incoming('+muac Alexis Coppola, F, 5months, green, oedema')
        self.assertEquals(s.eav.muac_category, 'G')
        self.assertEquals(s.eav.muac_ignored, 'T')

    def testEpi(self):
        s = fake_incoming('+epi bd 5,ma 12,tb 1,ab 2,af 3,mg 4,me 5, ch 6, gw 7, nt 8, yf 9, pl 10, ra 11, vf 12, ei 13')
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

        #new EPI doesn't require +, and has dy and rb indicators
        s = fake_incoming('epi dy 5,ma 12,tb 1,ab 2,af 3,mg 4,me 5, ch 6, gw 7, nt 8, yf 9, pl 10, rb 11, vf 12, ei 13')
        # DY should alias to BD to make reporting easier (since they're actually the same indicator
        self.assertEquals(s.eav.epi_bd, 5)
        self.assertEquals(s.eav.epi_dy, 5)
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
        # RB should alias to RB to make reporting easier (since they're actually the same indicator
        self.assertEquals(s.eav.epi_ra, 11)
        self.assertEquals(s.eav.epi_rb, 11)
        self.assertEquals(s.eav.epi_vf, 12)
        self.assertEquals(s.eav.epi_ei, 13)

    def testHome(self):
        s = fake_incoming('+home 13, wa 9, it 10, la 11, ha 12')
        self.assertEquals(s.eav.home_wa, 9)
        self.assertEquals(s.eav.home_it, 10)
        self.assertEquals(s.eav.home_la, 11)
        self.assertEquals(s.eav.home_ha, 12)
        self.assertEquals(s.eav.home_to, 13)

    def testCom(self):
        s = fake_incoming('com 1, 2, 3, 4, 5, 6, 7')
        self.assertEquals(s.eav.com_fever, 1)
        self.assertEquals(s.eav.com_diarrhea, 2)
        self.assertEquals(s.eav.com_death, 3)
        self.assertEquals(s.eav.com_bi_od, 4)
        self.assertEquals(s.eav.com_muac_red, 5)
        self.assertEquals(s.eav.com_muac_yellow, 6)
        self.assertEquals(s.eav.com_muac_green, 7)

    def testMal(self):
        s = fake_incoming('mal 1, 2, 3, 4')
        self.assertEquals(s.eav.mal_total_new, 1)
        self.assertEquals(s.eav.mal_total_death, 2)
        self.assertEquals(s.eav.mal_total_default, 3)
        self.assertEquals(s.eav.mal_total_admissions, 4)

    def testRutf(self):
        s = fake_incoming('rutf 1, 2, 3, 4')
        self.assertEquals(s.eav.rutf_new_f75_stock, 1)
        self.assertEquals(s.eav.rutf_closing_f75_stock, 2)
        self.assertEquals(s.eav.rutf_new_rutf_stock, 3)
        self.assertEquals(s.eav.rutf_closing_rutf_stock, 4)

    def testACT(self):
        s = fake_incoming('act 1, 2, 3, 4, 5, 6, 7, 8, 9, 10')
        self.assertEquals(s.eav.act_yellow_disp, 1)
        self.assertEquals(s.eav.act_yellow_balance, 2)
        self.assertEquals(s.eav.act_blue_disp, 3)
        self.assertEquals(s.eav.act_blue_balance, 4)
        self.assertEquals(s.eav.act_brown_disp, 5)
        self.assertEquals(s.eav.act_brown_balance, 6)
        self.assertEquals(s.eav.act_green_disp, 7)
        self.assertEquals(s.eav.act_green_balance, 8)
        self.assertEquals(s.eav.act_other_disp, 9)
        self.assertEquals(s.eav.act_other_balance, 10)

    def testTimeDeltas(self):
        s = fake_incoming('+muac Sean Blaschke, M,5months,yellow')
        pe = PatientEncounter.objects.get(submission=s)
        p = pe.patient
        self.failUnless(p.age.days - 150 < 2)

        s = fake_incoming('+muac Sean Blaschke, M,2 wks,yellow')
        pe = PatientEncounter.objects.get(submission=s)
        p = pe.patient
        self.failUnless(p.age.days - 14 < 2)

        s = fake_incoming('+muac Sean Blaschke, M,3 yeers,yellow')
        pe = PatientEncounter.objects.get(submission=s)
        p = pe.patient
        self.failUnless(p.age.days - 1095 < 2)

        s = fake_incoming('+muac Sean Blaschke, M,2 dys,yellow')
        pe = PatientEncounter.objects.get(submission=s)
        p = pe.patient
        self.failUnless(p.age.days - 2 < 2)

    def testValidity(self):
        s = fake_incoming('+muac Sean Blascke, M,2 dys,yellow')
        s1 = fake_incoming('+muac Sean Blaschke, M,2 dys,yellow')
        s = XFormSubmission.objects.get(pk=s.pk)
        self.assertEquals(s.has_errors, True)
        self.failIf(PatientEncounter.objects.get(submission=s).valid)

        s = fake_incoming('+birth terra weikel, F, Home')
        s1 = fake_incoming('+birth terra weikel, F, Facility')
        s = XFormSubmission.objects.get(pk=s.pk)
        self.assertEquals(s.has_errors, True)
        self.failIf(PatientEncounter.objects.get(submission=s).valid)

        s = fake_incoming('+DEATH maltheSMS, M, 2Y')
        s1 = fake_incoming('+DEATH maltheSMS, M, 3Y')
        s = XFormSubmission.objects.get(pk=s.pk)
        self.assertEquals(s.has_errors, True)
        self.failIf(PatientEncounter.objects.get(submission=s).valid)

        s = fake_incoming('+epi bd 5,ma 12,tb 1,ab 2,af 3,mg 4,me 5, ch 6, gw 7, nt 8, yf 9, pl 10, ra 11, vf 12, ei 13')
        s1 = fake_incoming('+epi bd 5,ma 12')
        s = XFormSubmission.objects.get(pk=s.pk)
        self.failUnless(s.has_errors)

        s = fake_incoming('+home 13, wa 9, it 10, la 11, ha 12')
        s1 = fake_incoming('+home 23, wa 9, it 10, la 11, ha 12')
        s = XFormSubmission.objects.get(pk=s.pk)
        self.failUnless(s.has_errors)

    def testPatientMatching(self):
        s = fake_incoming('+muac Sean Blascke, M,2 dys,yellow')
        s1 = fake_incoming('+muac Sean Blaschke, M,2 dys,yellow')
        self.assertEquals(s.report.patient.pk, s1.report.patient.pk)
        p = s1.report.patient
        self.assertEquals(p.last_name, 'Blaschke')

    def testRegister(self):
        b = Backend.objects.get(name='test')
        c = Connection.objects.create(identity='8675310', backend=b)
        s = fake_incoming('+muac Sean Blaschke, M,2 dys,yellow', c)
        self.failUnless(s.has_errors)
        c = Connection.objects.get(identity='8675310')
        s = fake_incoming('+reg David McCann', c)
        c = Connection.objects.get(identity='8675310')
        self.assertEquals(c.contact.name, 'David McCann')
        c.contact.active = True
        c.contact.save()
        s = fake_incoming('+muac Sean Blaschke, M,2 dys,yellow', c)
        self.failIf(s.has_errors)

    def testVHTRegistration(self):
        ht = HealthFacilityType.objects.create(name="Drug Store", slug="ds")
        hc = HealthFacility.objects.create(name="Dave's Drug Emporium", code="AWESOME", type=ht)
        s = fake_incoming('+vht AWESOME')
        self.assertEquals(hc, HealthProvider.objects.all()[0].facility)

    def testDoubleRegister(self):
        fake_incoming('+reg newname')
        self.assertEquals(Contact.objects.all()[0].name, 'newname')

    def testResponses(self):
        fake_incoming('+reg David McCann')
        self.incomingResponse('+BIRTH Terra Weikel, F, HOME', 'Thank you for registering the birth of Terra Weikel, female (infant). We have recorded that the birth took place at home.')
        self.incomingResponse('+DEATH Malthe Borch, M,1DAY', 'We have recorded the death of Malthe Borch, male (infant).')
        self.incomingResponse('+muac Matt Berg, M,5months,yellow', 'Matt Berg, male (5 months old) has been identified with Risk of Malnutrition')
        self.incomingResponse('+epi ma 12, bd 5', 'You reported Malaria 12, and Bloody diarrhea (Dysentery) 5.If there is an error,please resend.')
        self.incomingResponse('+home 12, wa 1, it 6', 'You reported Total Homesteads Visited 12,Safe Drinking Water 1, and ITTNs/LLINs 6.If there is an error,please resend.')

    def testErrors(self):
        #TODO make proper fields required
        self.fakeErrorMessage('+birth apio')
        self.fakeErrorMessage('+birth apio, f')
        self.fakeErrorMessage('+birth api, f, bed')
        self.fakeErrorMessage('+death apio')
        self.fakeErrorMessage('+death apio, f')
        self.fakeErrorMessage('+death apio, f, other')
        self.fakeErrorMessage('+muac foo')
        self.fakeErrorMessage('+muac foo, m')
        self.fakeErrorMessage('+muac foo, m, 16y')
        self.fakeErrorMessage('+muac foo, m, 31/12/1999, red')
        self.fakeErrorMessage('+epi ma')
        self.fakeErrorMessage('+epi ma 5 ma 10')
#        self.fakeErrorMessage('+epi MA -5')
        self.fakeErrorMessage('+epi xx 5.0')
        self.fakeErrorMessage('+epi ma five')
        self.fakeErrorMessage('+home wa')
        self.fakeErrorMessage('+home wa 5 wa 10')
#        self.fakeErrorMessage('+home WA -5')
        self.fakeErrorMessage('+home xx 5.0')
        self.fakeErrorMessage('+home wa five')

#    def testLocationDelete(self):
#        parent_loc = Location.objects.create(name='Uganda')
#        child_loc = Location.objects.create(name='Pader', tree_parent=parent_loc)
#        child_loc.save()
#        h = HealthFacility.objects.create(name="Dave's drug emporium")
#        h.catchment_areas.add(child_loc)
#        c = Contact.objects.create(name='Davey Crockett', reporting_location = parent_loc)
#        child_loc.delete()
#        c = Contact.objects.get(pk=c.pk)
#        h = HealthFacility.objects.get(pk=h.pk)
#        self.assertEquals(c.reporting_location, parent_loc)
#        self.assertEquals(h.catchment_areas.all()[0], parent_loc)
