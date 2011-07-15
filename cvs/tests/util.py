from rapidsms.models import Connection, Backend
from rapidsms_httprouter.models import Message
from rapidsms.messages.incoming import IncomingMessage
from rapidsms_xforms.models import XForm

def fake_incoming(message, connection=None):
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
