'''
Created on Jul 12, 2011

@author: asseym
'''
from django.core.management.base import BaseCommand
from script.models import *
from poll.models import *

class Command(BaseCommand):
    
    def handle(self, **options):
        script = Script.objects.create(
                slug="cvs_autoreg",
                name="CVS autoregistration script",
        )
        user = User.objects.get(username="admin")
        script.sites.add(Site.objects.get_current())
        
        ## role of CVS reporter
        description = 'CVS Reporter Role'
        question = 'Welcome to RapidSMS, the Ministry of Health’s data collection system. What is your role?'
        default_response = 'Thank you for starting the registration process'
        type = Poll.TYPE_TEXT
        role_poll = Poll.objects.create(name=description,question=question,default_response=default_response,type=type, user=user)
        role_poll.sites.add(Site.objects.get_current())
        vht_category = role_poll.categories.add(name='VHT')
        vht_category.response = "Thank you for starting the registration process" 
        vht_category.color = '99ff77'
        vht_category.save()
        pvht_category = role_poll.categories.add(name='PVHT')
        pvht_category.response = "Thank you for starting the registration process" 
        pvht_category.color = 'ff9977'
        pvht_category.save()
        hc_category = role_poll.categories.add(name='HC')
        hc_category.response = "Thank you for starting the registration process" 
        hc_category.color = 'ff7799'
        hc_category.save()
        hf_category = role_poll.categories.add(name='HF')
        hf_category.response = "Thank you for starting the registration process" 
        hf_category.color = '77ff99'
        hf_category.save()
        dht_category = role_poll.categories.add(name='DHT')
        dht_category.response = "Thank you for starting the registration process" 
        dht_category.color = '66ff99'
        dht_category.save()
        dht_category = role_poll.categories.add(name='DHO')
        dho_category.response = "Thank you for starting the registration process" 
        dho_category.color = 'ff6699'
        dho_category.save()
        unknown_category = role_poll.categories.get(name='unknown')
        unknown_category.default = False
        unknown_category.color = 'ffff77'
        unknown_category.save()
        unclear_category = Category.objects.create(
            poll=role_poll,
            name='unclear',
            default=True,
            color='ffff77',
            response='We did not understand your answer. Kindly note that this number is for official use only',
            priority=3
        )
        role_poll.start()
    
        script.steps.add(ScriptStep.objects.create(
            script=script,
            poll=role_poll,
            order=0,
            rule=ScriptStep.WAIT_MOVEON,
            start_offset=0,
            giveup_offset=60,
        ))
        
        ## CVS reporter Name
        description = 'CVS Reporter Name'
        question = 'Please enter only the answers to the questions asked. What is your name?'
        default_response = 'Thank you for your response'
        type = Poll.TYPE_TEXT
        name_poll = Poll.objects.create(name=description, question=question, default_response=default_response, type=type, user=user)
        name_poll.sites.add(Site.objects.get_current())
        name_poll.start()
        
        script.steps.add(ScriptStep.objects.create(
               script=consignee_script,
               poll=name_poll,
               order=1,
               rule=ScriptStep.RESEND_GIVEUP,
               start_offset=0,
               retry_offset=60 * 15,
               give_up_offset=60*30,
               num_tries=3,
               ))
        
        ## CVS reporter District
        description = 'CVS Reporter District'
        question = 'What is the name of your District?'
        default_response = 'Thank you for your response'
        type = Poll.TYPE_TEXT
        district_poll = Poll.objects.create(name=description, question=question, default_response=default_response, type=type, user=user)
        district_poll.sites.add(Site.objects.get_current())
        district_poll.start()
        
        script.steps.add(ScriptStep.objects.create(
               script=consignee_script,
               poll=district_poll,
               order=2,
               rule=ScriptStep.RESEND_GIVEUP,
               start_offset=0,
               retry_offset=60 * 15,
               give_up_offset=60*30,
               num_tries=3,
               ))
        
        ## CVS reporter Health Facility
        description = 'CVS Reporter HF'
        question = 'What is the name of your Health Facility?'
        default_response = 'Thank you for your response'
        type = Poll.TYPE_TEXT
        hf_poll = Poll.objects.create(name=description, question=question, default_response=default_response, type=type, user=user)
        hf_poll.sites.add(Site.objects.get_current())
        hf_poll.start()
        
        script.steps.add(ScriptStep.objects.create(
               script=consignee_script,
               poll=hf_poll,
               order=3,
               rule=ScriptStep.RESEND_GIVEUP,
               start_offset=0,
               retry_offset=60 * 15,
               give_up_offset=60*30,
               num_tries=3,
               ))
        
        ## CVS reporter Village
        description = 'CVS Reporter Village'
        question = 'What is the name of your Village?'
        default_response = 'Thank you for your response'
        type = Poll.TYPE_TEXT
        village_poll = Poll.objects.create(name=description, question=question, default_response=default_response, type=type, user=user)
        village_poll.sites.add(Site.objects.get_current())
        village_poll.start()
        
        script.steps.add(ScriptStep.objects.create(
               script=consignee_script,
               poll=village_poll,
               order=4,
               rule=ScriptStep.RESEND_GIVEUP,
               start_offset=0,
               retry_offset=60 * 15,
               give_up_offset=60*30,
               num_tries=3,
               ))
        
        ## CVS reporter Alternative Phone numbers
        description = 'CVS Reporter numbers'
        question = 'Do you have any other phone numbers?'
        default_response = 'Thanks for registering! You have just entered training mode.'
        type = Poll.TYPE_TEXT
        numbers_poll = Poll.objects.create(name=description, question=question, default_response=default_response, type=type, user=user)
        numbers_poll.sites.add(Site.objects.get_current())
        numbers_poll.start()
        
        script.steps.add(ScriptStep.objects.create(
               script=consignee_script,
               poll=numbers_poll,
               order=5,
               rule=ScriptStep.LINIENT,
               ))
        