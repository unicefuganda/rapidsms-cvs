from rapidsms.models import Contact
from django.conf import settings
from rapidsms.apps.base import AppBase
from script.models import ScriptProgress, Script
from unregister.models import Blacklist

class App (AppBase):

    def handle (self, message):
        opt_out_words = [w.lower() for w in getattr(settings, 'OPT_OUT_WORDS', [])]
        opt_in_words = [w.lower() for w in getattr(settings, 'OPT_IN_WORDS', [])]
        if getattr(settings, 'ACTIVATION_CODE', None) and message.text.strip().lower().startswith(settings.ACTIVATION_CODE.lower()):
            if not message.connection.contact:
                message.respond('You must first register with the system.Text JOIN to 6767 to begin.')
                return True
            if not message.connection.contact.active:
                message.connection.contact.active = True
                message.connection.contact.save()
                message.respond(getattr(settings, 'ACTIVATION_MESSAGE', 'Congratulations, you are now active in the system!'))
                return True
            else:
                message.respond(getattr(settings, 'ALREADY_ACTIVATED_MESSAGE', 'You are already in the system.You should not SMS the code %s' % getattr(settings, 'ACTIVATION_CODE')))
                return True
        elif message.text.strip().lower() in opt_out_words:
            Blacklist.objects.create(connection=message.connection)
            if (message.connection.contact):
                message.connection.contact.active = False
                message.connection.contact.save()
            message.respond(getattr(settings, 'OPT_OUT_CONFIRMATION', 'You have just quit.'))
            return True
        elif message.text.strip().lower() in opt_in_words:
            blacklists = Blacklist.objects.filter(connection=message.connection)
            if blacklists.count() or not message.connection.contact:
                blacklists.delete()
                ScriptProgress.objects.create(script=Script.objects.get(slug="cvs_autoreg"), \
                                          connection=message.connection)
            else:
                message.respond("You are already in the system and do not need to 'Join' again.Only if you want to reregister,or change location,please send the word JOIN to 6767.")
            return True
        elif Blacklist.objects.filter(connection=message.connection).count():
            return True
        return False

    def outgoing(self, msg):
        if Blacklist.objects.filter(connection=msg.connection).count() and msg.text != getattr(settings, 'OPT_OUT_CONFIRMATION', 'You have just quit.'):
            return False
        return True
