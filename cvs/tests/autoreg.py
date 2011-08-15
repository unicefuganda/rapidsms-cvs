"""
Autoreg tests for CVS
"""

from cvs.utils import *
from django.conf import settings
from django.contrib.auth.models import User, Group
from django.test import TestCase
from healthmodels.models import *
from healthmodels.models.HealthFacility import HealthFacility
from poll.utils import create_attributes
from rapidsms.contrib.locations.models import Location, LocationType
from rapidsms.messages.incoming import IncomingMessage, IncomingMessage
from rapidsms.models import Connection, Backend, Contact
from rapidsms_httprouter.models import Message
from rapidsms_httprouter.router import get_router
from rapidsms_xforms.models import *
from script.models import Script, ScriptProgress, ScriptSession, ScriptResponse
from script.signals import script_progress_was_completed, script_progress
from script.utils.outgoing import check_progress
from unregister.models import Blacklist
import datetime
import traceback
from rapidsms_httprouter.router import get_router, HttpRouterThread

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


    def assertResponseEquals(self, message, expected_response, connection=None):
        s = self.fake_incoming(message, connection)
        self.assertEquals(s.response, expected_response)


    def fake_submission(message, connection=None):
        form = XForm.find_form(message)
        if connection is None:
            try:
                connection = Connection.objects.all()[0]
            except IndexError:
                backend, created = Backend.objects.get_or_create(name='test')
                connection, created = Connection.objects.get_or_create(identity='8675309',
                                                                       backend=backend)
        # if so, process it
        incomingmessage = IncomingMessage(connection, message)
        incomingmessage.db_message = Message.objects.create(direction='I', connection=connection, text=message)
        if form:
            submission = form.process_sms_submission(incomingmessage)
            return submission
        return None


    def fake_error_submission(self, message, connection=None):
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

    def setUp(self):
        if 'django.contrib.sites' in settings.INSTALLED_APPS:
            site_id = getattr(settings, 'SITE_ID', 1)
            Site.objects.get_or_create(pk=site_id, defaults={'domain':'rapidcvs.org'})
        init_groups()
        init_autoreg(None)
        create_attributes()
        User.objects.get_or_create(username='admin')
        self.backend = Backend.objects.create(name='test')
        self.connection = Connection.objects.create(identity='8675309', backend=self.backend)
        country = LocationType.objects.create(name='country', slug='country')
        district = LocationType.objects.create(name='district', slug='district')
        village = LocationType.objects.create(name='village', slug='village')
        self.root_node = Location.objects.create(type=country, name='Uganda')
        self.kampala_district = Location.objects.create(type=district, name='Kampala')
        self.makindye_village = Location.objects.create(type=village, name='Makindye')
        self.ntinda_village = Location.objects.create(type=village, name='Ntinda')
        self.mulago_healthfacility = HealthFacility.objects.create(name="Mulago")
        self.mengo_healthfacility = HealthFacility.objects.create(name="Mengo")
        def test_run(self):
             return
        HttpRouterThread.run = test_run



    def fake_script_dialog(self, script_prog, connection, responses, emit_signal=True):
        script = script_prog.script
        ss = ScriptSession.objects.create(script=script, connection=connection, start_time=datetime.datetime.now())
        for poll_name, resp in responses:
            poll = script.steps.get(poll__name=poll_name).poll
            poll.process_response(self.spoof_incoming_obj(resp))
            resp = poll.responses.all().order_by('-date')[0]
            ScriptResponse.objects.create(session=ss, response=resp)
        ss.end_time = datetime.datetime.now()
        ss.save()
        if emit_signal:
            script_progress_was_completed.send(connection=connection, sender=script_prog)
        return ss

    def testBasicAutoReg(self):
        self.fake_incoming('join')
        self.assertEquals(ScriptProgress.objects.count(), 1)
        script_prog = ScriptProgress.objects.all()[0]
        self.assertEquals(script_prog.script.slug, 'cvs_autoreg')

        self.fake_script_dialog(script_prog, self.connection, [\
            ('cvs_role', 'vht'), \
            ('cvs_name', 'testy mctesterton'), \
            ('cvs_district', 'kampala'), \
            ('cvs_healthfacility', 'mulago'), \
            ('cvs_village', 'makindye'), \
        ])

        contact = Contact.objects.all()[0]
        self.assertEquals(contact.groups.all()[0].name, 'VHT')
        self.assertEquals(contact.name, 'Testy Mctesterton')
        self.assertEquals(contact.reporting_location, self.kampala_district)
        self.assertEquals(contact.village, self.makindye_village)
        self.assertEquals(HealthProvider.objects.get(pk=contact.pk).facility, self.mulago_healthfacility)
        self.assertEquals(Contact.objects.count(), 1)
        self.assertEquals(HealthProvider.objects.count(), 1)

    def testBadAutoReg(self):
        """
        Crummy answers
        """
        self.fake_incoming('join')
        script_prog = ScriptProgress.objects.all()[0]
        self.fake_script_dialog(script_prog, self.connection, [\
            ('cvs_role', 'bodaboda'), \
            ('cvs_district', 'kitgum'), \
            ('cvs_village', 'amudat'), \
            ('cvs_name', 'bad tester'), \
        ])
        self.assertEquals(Contact.objects.count(), 1)
        contact = Contact.objects.all()[0]
        self.assertEquals(contact.groups.all()[0].name, 'Other CVS Reporters')
        self.assertEquals(contact.reporting_location, self.root_node)
        self.assertEquals(contact.village, None)
        self.assertEquals(contact.name, 'Bad Tester')
        self.assertEquals(HealthProvider.objects.count(), 0)

    def testMultipleRegistrations(self):

        self.fake_incoming('join')
        script_prog = ScriptProgress.objects.all()[0]
        self.fake_script_dialog(script_prog, self.connection, [\
            ('cvs_role', 'vht'), \
            ('cvs_name', 'testy mctesterton'), \
            ('cvs_district', 'kampala'), \
            ('cvs_healthfacility', 'mulago hospital'), \
            ('cvs_village', 'makindye'), \
        ])

        #Same fellow joins again with a different number
        backend, created = Backend.objects.get_or_create(name='test')
        connection, created = Connection.objects.get_or_create(identity='9675309', backend=backend)

        self.fake_incoming('join', connection=connection)
        script_prog = ScriptProgress.objects.all()[1]
        self.fake_script_dialog(script_prog, script_prog.connection, [\
            ('cvs_role', 'vht'), \
            ('cvs_name', 'testy mctesterton'), \
            ('cvs_district', 'kampala'), \
            ('cvs_healthfacility', 'mulago hospita1'), \
            ('cvs_village', 'makindye'), \
        ])

        self.assertEquals(Contact.objects.count(), 1)
        self.assertEquals(HealthProvider.objects.count(), 1)
        self.assertEquals(Connection.objects.filter(contact=Contact.objects.all()[0]).count(), 2)
        contact = Contact.objects.all()[0]
        self.assertEquals(HealthProvider.objects.get(pk=contact.pk).facility, self.mulago_healthfacility)

    def testQuitRejoin(self):

        self.fake_incoming('join')
        script_prog = ScriptProgress.objects.all()[0]
        self.fake_script_dialog(script_prog, self.connection, [\
            ('cvs_role', 'vht'), \
            ('cvs_name', 'testy mctesterton'), \
            ('cvs_district', 'kampala'), \
            ('cvs_healthfacility', 'mulago hospital'), \
            ('cvs_village', 'makindye'), \
        ])

        contact = Contact.objects.all()[0]
        self.assertEquals(HealthProvider.objects.get(pk=contact.pk).facility, self.mulago_healthfacility)

        #Fellow quits the system
        self.fake_incoming('quit')

        self.assertEquals(Contact.objects.count(), 1)
        contact = Contact.objects.all()[0]
        self.assertEquals(contact.active, False)
        self.assertEquals(Blacklist.objects.count(), 1)

        #First Cleanup ScriptProgress to pave way for rejoining
        ScriptProgress.objects.all().delete()

        #Same fellow now starts reporting for different hospital altogether but same locality
        self.fake_incoming('join')
        script_prog = ScriptProgress.objects.all()[0]
        self.fake_script_dialog(script_prog, self.connection, [\
            ('cvs_role', 'vht'), \
            ('cvs_name', 'testy mctesterton'), \
            ('cvs_district', 'kampala'), \
            ('cvs_healthfacility', 'mengo'), \
            ('cvs_village', 'makindye'), \
        ])

        self.assertEquals(Contact.objects.count(), 1)
        self.assertEquals(HealthProvider.objects.count(), 1)
        self.assertEquals(Blacklist.objects.count(), 0)
        contact = Contact.objects.all()[0]
        self.assertEquals(HealthProvider.objects.get(pk=contact.pk).facility, self.mengo_healthfacility)
        self.assertEquals(contact.name, 'Testy Mctesterton')

    def testActivateAutoReg(self):

        #attempt activation without registering
        resp = self.fake_incoming(getattr(settings, 'ACTIVATION_CODE', '1234'))
        self.assertEquals(resp.responses.all()[0].text, 'You must first register with the system.Text JOIN to 6767 to begin.')

        #user joins
        self.fake_incoming('join')
        script_prog = ScriptProgress.objects.all()[0]
        self.fake_script_dialog(script_prog, self.connection, [\
            ('cvs_role', 'vht'), \
            ('cvs_name', 'testy mctesterton'), \
            ('cvs_district', 'kampala'), \
            ('cvs_healthfacility', 'mengo'), \
            ('cvs_village', 'makindye'), \
        ])

        self.assertEquals(Contact.objects.all()[0].active, False)

        #activate registration 
        resp = self.fake_incoming(getattr(settings, 'ACTIVATION_CODE', '1234'))
        self.assertEquals(resp.responses.all()[0].text, getattr(settings, 'ACTIVATION_MESSAGE', 'Congratulations, you are now active in the system!'))
        self.assertEquals(Contact.objects.all()[0].active, True)

        #activate registration again
        resp = self.fake_incoming(getattr(settings, 'ACTIVATION_CODE', '1234'))
        self.assertEquals(resp.responses.all()[0].text, getattr(settings, 'ALREADY_ACTIVATED_MESSAGE', 'You are already in the system.You should not SMS the code %s' % getattr(settings, 'ACTIVATION_CODE')))
