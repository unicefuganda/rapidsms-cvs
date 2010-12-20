from rapidsms_xforms.models import XFormField, dl_distance, xform_received
import re
import datetime
from healthmodels.models import *
from simple_locations.models import Point, Area, AreaType
from code_generator.code_generator import get_code_from_model, generate_tracking_tag, generate_code

def parse_timedelta(command, value):
    lvalue = value.lower().strip()
    now = datetime.datetime.now()
    try:
        return (now -  datetime.datetime.strptime(lvalue, '%m-%d-%Y')).days
    except ValueError:
        try:
            return (now -  datetime.datetime.strptime(lvalue, '%m/%d/%Y')).days
        except ValueError:            
            rx = re.compile('[0-9]*')
            m = rx.match(lvalue)
            number = lvalue[m.start():m.end()].strip()
            unit = lvalue[m.end():].strip()
            if number:
                number = int(number)
                unit_dict = {
                    ('day','days','dys','ds','d'):1,
                    ('week', 'wk','wks','weeks','w'):7,
                    ('month', 'mo','months','mnths','mos','ms','mns','mnth','m'):30,
                    ('year', 'yr','yrs','y'):365,
                }
                for words, days in unit_dict.iteritems():
                    for word in words:
                        if dl_distance(word, value) <= 1:
                            return days    
            
    raise ValidationError("Expected an age got: %s." % value)
    #do something to parse a time delta
    #raise ValidationError("unknown time length or something")

    #cleaned_value = like a timedelta or something
    #return cleaned_value

# register timedeltas as a type

def parse_place(command, value):
    lvalue = value.lower().strip()
    for w in ('clinic', 'facility', 'hc','hospital'):
        if dl_distance(lvalue, w) <= 1:
            return 'FACILITY'
    if dl_distance(lvalue, 'home') <= 1:
        return 'HOME'
    else:
        raise ValidationError("Did not understand the location: %s." % value)

def parse_gender(command, value):
    # return m or f
    lvalue = value.lower().strip()
    if (lvalue == 'm') or (dl_distance(lvalue, 'male') <= 1):
        return 'M'
    elif (lvalue == 'f') or (dl_distance(lvalue, 'female') <= 1):
        return 'F'
    else:
        raise ValidationError("Expected the patient's gender "
                    "(\"male\", \"female\", or simply \"m\" or \"f\"), "
                    "but received instead: %s." % value)

def parse_muacreading(command, value):
    print "paring muacreading"
    lvalue = value.lower().strip()
    rx = re.compile('[0-9]*')
    m = rx.match(lvalue)
    reading = lvalue[m.start():m.end()]
    remaining = lvalue[m.end():].strip() 
    try:
        reading = int(reading)
        if remaining == 'mm':
            if reading <= 30:
                reading *= 10
        elif remaining == 'cm':
            reading *= 10
        if reading > 125:
            return'G'
        elif reading < 114:
            return 'R'
        else:
            return 'Y'
    except ValueError:
        for category, word in (('R', 'red'), ('Y','yellow'), ('G','green')):
            if (remaining == category.lower()) or (dl_distance(lvalue, word) <= 1):
                return category

def parse_oedema(command, value):
    lvalue = value.lower().strip()
    if dl_distance(lvalue, 'oedema') <= 1:
        return 'T'
    else:
        return 'F'

XFormField.register_field_type('cvssex', 'Gender', parse_gender,
                               db_type=XFormField.TYPE_TEXT, xforms_type='string')

XFormField.register_field_type('cvsloc', 'Place', parse_place,
                               db_type=XFormField.TYPE_TEXT, xforms_type='string')

XFormField.register_field_type('cvstdelt', 'Time Delta', parse_timedelta,
                               db_type=XFormField.TYPE_INT, xforms_type='integer')

XFormField.register_field_type('cvsmuacr', 'Muac Reading', parse_muacreading,
                               db_type=XFormField.TYPE_TEXT, xforms_type='string')

XFormField.register_field_type('cvsodema', 'Oedema Occurrence', parse_oedema,
                               db_type=XFormField.TYPE_TEXT, xforms_type='string')

def xform_received_handler(sender, **kwargs):
    xform = kwargs['xform']
    submission = kwargs['submission']

    # TODO: create patient
    # TODO: check validity
    # TODO: where's the message FK?
    patient = None
    valid = True
    kwargs.setdefault('message', None)
    message = kwargs['message']

    if xform.keyword == 'muac':
        report = PatientEncounter.objects.create(
                submission=submission,
                reporter=submission.contact.healthproviderbase.healthprovider,
                patient=patient,
                message=message,
                valid=valid)
        patient.health_worker=submission.connection.contact.healthproviderbase.healthprovider
        patient.save()
    elif xform.keyword == 'birth':
        names = submission.eav.birth_name.split(' ')
        first_name = names[0]
        last_name = ''
        middle_name = ''
        if len(names) > 1:
            last_name = names[len(names) - 1]
        if len(names) > 2:
            middle_name = ' '.join(names[1:-1])

        healthcode = generate_tracking_tag()
        if HealthId.objects.count():
            healthcode = HealthId.objects.order_by('-pk')[0].health_id
            healthcode = generate_tracking_tag(healthcode)
        healthid = HealthId.objects.create(
            health_id = healthcode
        )
        healthid.save()
        patient = Patient.objects.create(
             health_id=healthid,
             first_name=first_name,
             middle_name=middle_name,
             last_name=last_name,
             gender=submission.eav.gender,
             birthdate=datetime.datetime.now(),
        )
        patient.save()
        healthid.issued_to = patient
        healthid.save()
        
        report = PatientEncounter.objects.create(
                submission=submission,
                reporter=submission.connection.contact.healthproviderbase.healthprovider,
                patient=patient,
                message=message,
                valid=valid)
        patient.health_worker=submission.connection.contact.healthproviderbase.healthprovider
        patient.save()                
    elif xform.keyword == 'death':
        report = PatientEncounter.objects.create(
                submission=submission,
                reporter=submission.connection.contact.healthproviderbase.healthprovider,
                patient=patient,
                message=message,
                valid=valid)
        patient.health_worker=submission.connection.contact.healthproviderbase.healthprovider
        patient.save()
    elif xform.keyword == 'itp':
        report = PatientEncounter.objects.create(
                submission=submission,
                reporter=submission.connection.contact.healthproviderbase.healthprovider,
                patient=patient,
                message=message,
                valid=valid)
        patient.health_worker=submission.connection.contact.healthproviderbase.healthprovider
        patient.save()
    elif xform.keyword == 'otp':
        report = PatientEncounter.objects.create(
                submission=submission,
                reporter=submission.connection.contact.healthproviderbase.healthprovider,
                patient=patient,
                message=message,
                valid=valid)
        patient.health_worker=submission.connection.contact.healthproviderbase.healthprovider
        patient.save()
    elif xform.keyword == 'cure':
        report = PatientEncounter.objects.create(
                submission=submission,
                reporter=submission.connection.contact.healthproviderbase.healthprovider,
                patient=patient,
                message=message,
                valid=valid)
        patient.health_worker=submission.connection.contact.healthproviderbase.healthprovider
        patient.save()

xform_received.connect(xform_received_handler, weak=True)