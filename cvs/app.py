from rapidsms.models import Contact
from django.conf import settings
from rapidsms.apps.base import AppBase

class App (AppBase):
    
    def handle (self, message):
        if getattr(settings, 'ACTIVATION_CODE',None) and message.text.strip().lower() == settings.ACTIVATION_CODE:
            if not message.connection.contact:
                message.connection.contact = Contact.objects.create(name='Anonymous User')
                message.connection.save()
            if not message.connection.contact.active:
                message.connection.contact.active=True
                message.connection.contact.save()
                message.respond(getattr(settings,'ACTIVATION_MESSAGE','Congratulations, you are now active in the system!'))
                return True
        return False
