'''
Created on Jul 12, 2011

@author: asseym
'''
from rapidsms.apps.base import AppBase
from script.models import *

class App (AppBase):
    '''
    classdocs
    '''

    def handle (self, message):
        if not message.connection.contact:
            message.connection.contact = Contact.objects.create(name='Anonymous User')
            message.connection.save()
            ScriptProgress.objects.create(script=Script.objects.get(slug="cvs_autoreg"),\
                                          connection=message.connection)
            return True
        return False

        