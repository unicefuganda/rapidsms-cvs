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

def get_or_create_patient(healthcare_provider, patient_name, birthdate=None, deathdate=None, gender=None):
    return create_patient(healthcare_provider, patient_name, birthdate, deathdate, gender)

def create_patient(healthcare_provider, patient_name, birthdate, deathdate, gender):
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
         gender=gender,
         birthdate=birthdate,
         deathdate=deathdate,
    )
    patient.save()
    healthid.issued_to = patient
    healthid.save()
    patient.health_worker=healthcare_provider
    patient.save()
    return patient

def check_validity(xform_type, healthcare_provider, patient=None):
    return True

def xform_received_handler(sender, **kwargs):
    xform = kwargs['xform']
    submission = kwargs['submission']

    # TODO: check validity
    patient = None
    kwargs.setdefault('message', None)
    message = kwargs['message']
    if not message:
        return

    health_provider = submission.connection.contact.healthproviderbase.healthprovider
    if xform.keyword == 'muac':
        days = submission.eav.muac_age
        birthdate = datetime.date.today() - datetime.timedelta(days=days)
        patient = get_or_create_patient(health_provider, submission.eav.muac_name, birthdate=birthdate, gender=submission.eav.muac_gender)
        valid = check_validity(xform.keyword, healthcare_provider, patient)                
        report = PatientEncounter.objects.create(
                submission=submission,
                reporter=health_provider,
                patient=patient,
                message=message,
                valid=valid)
    elif xform.keyword == 'birth':
        patient = create_patient(health_provider, submission.eav.birth_name, birthdate=datetime.datetime.now(), gender=submission.eav.birth_gender)
        valid = check_validity(xform.keyword, healthcare_provider, patient)
        report = PatientEncounter.objects.create(
                submission=submission,
                reporter=submission.connection.contact.healthproviderbase.healthprovider,
                patient=patient,
                message=message,
                valid=valid)                
    elif xform.keyword == 'death':
        days = submission.eav.death_age
        birthdate = datetime.date.today() - datetime.timedelta(days=days)
        patient = get_or_create_patient(health_provider, submission.eav.death_name, birthdate=birthdate, gender=submission.eav.death_gender, deathdate=datetime.date.today())
        valid = check_validity(xform.keyword, healthcare_provider, patient)                
        report = PatientEncounter.objects.create(
                submission=submission,
                reporter=health_provider,
                patient=patient,
                message=message,
                valid=valid)

xform_received.connect(xform_received_handler, weak=True)