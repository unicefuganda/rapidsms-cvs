from rapidsms.models import Connection
from rapidsms_httprouter.models import Message
from rapidsms.messages.incoming import IncomingMessage
from rapidsms_xforms.models import XForm

def fake_incoming(message, connection=None):
    form = XForm.find_form(message)

    if connection is None:
        connection = Connection.objects.all()[0]
    # if so, process it
    incomingmessage = IncomingMessage(connection, message)
    incomingmessage.db_message = Message.objects.create(direction='I', connection=Connection.objects.all()[0], text=message)
    if form:
        submission = form.process_sms_submission(incomingmessage)
        return submission
    return None
