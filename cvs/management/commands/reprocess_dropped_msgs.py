'''
Created on Aug 24, 2012

@author: asseym
'''
from django.core.management.base import BaseCommand
import traceback
import os
from rapidsms.models import Connection
from rapidsms_httprouter.models import Message
from optparse import OptionParser, make_option
import urllib2
import urllib
import time

class Command(BaseCommand):

    option_list = BaseCommand.option_list + (
            make_option("-d", "--dry_run", dest="dry_run"),
            make_option("-f", "--file", dest="file"),
            make_option("-c", "--code", dest="code"),
            make_option("-p", "--password", dest="password")
        )

    def handle(self, **options):

        dry_run = options['dry_run']
        log_file = options['file']
        code = options['code']
        password = options['password']

        if not log_file:
            log_file = raw_input('Access log to be processed:')
        if not log_file:
            log_file = "/Users/asseym/Desktop/tmp/mtrack_prod.access.log.1"
        if not code:
            code = '6767'
#        import pdb;pdb.set_trace()
        file_handle=open(log_file)
        lines=file_handle.readlines()
#        client = Client()
        for line in lines:
#            time.sleep(2)
            if line.find('router') and line.find('receive'):
                parts = line.strip().rsplit(' ')
                http_status = parts[8]
                query_string = parts[6]
                query_parts = query_string.split('=')
                try:
                    count = 0
                    backend_str = query_parts[2][:-7]
                    connection = query_parts[3]
                    msg_str = urllib2.unquote(query_parts[4]).replace('+', ' ')
                    if connection.endswith('&message'):
                        if not http_status in ['200', '400']:
                            if backend_str in ['dmark', 'zain', 'yo8200']:
                                identity_str = connection[3:15] if connection.startswith('%') else connection[:12]
                                if not identity_str == 'Warid&messag':
                                    print identity_str, msg_str, http_status
                                    try:
                                        conn=Connection.objects.get(identity=identity_str, backend__name=backend_str)
                                        msg=Message.objects.filter(connection=conn, text=msg_str, direction="I")
                                        if msg.exists():
                                            print msg, ' --- exists!'
                                        else:
                                            if not dry_run:
                                                post_data = [('password', password),('backend', backend_str), ('sender', identity_str), ('message', msg_str)]     # a sequence of two element tuples
                                                result = urllib2.urlopen('http://cvs.rapidsms.org/router/receive/', urllib.urlencode(post_data))
                                            else:
                                                print msg_str, ' --- to be created'
                                    except Connection.DoesNotExist:
                                        print identity_str, ' --- connection does not exists'
                except IndexError:
                    pass