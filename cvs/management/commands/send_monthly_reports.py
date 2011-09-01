'''
Created on Sep 1, 2011

@author: asseym
'''
from django.core.management.base import BaseCommand
from cvs.utils import monthly_reports

class Command(BaseCommand):

    def handle(self, **options):
        monthly_reports()
