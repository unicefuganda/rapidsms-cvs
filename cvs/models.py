from rapidsms_xforms.models import XFormField, XForm, XFormSubmission, dl_distance, xform_received
import re
import datetime
from healthmodels.models import *
from healthmodels.models.HealthProvider import HealthProviderBase
from simple_locations.models import Point, Area, AreaType
from django.core.exceptions import ValidationError
from code_generator.code_generator import get_code_from_model, generate_tracking_tag, generate_code
from django.contrib.auth.models import Group
from django.db.models.signals import pre_delete
from rapidsms.models import Contact
from poll.models import Poll
from eav.models import Attribute
from cvs.forms import FacilityResponseForm

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
                unit_amounts = {
                    'd':1,
                    'w':7,
                    'm':30,
                    'y':365,
                }
                unit_dict = {
                    'd':('day','days','dys','ds'),
                    'w':('wk','wks','weeks','week'),
                    'm':('mo','months','month','mnths','mos','ms','mns','mnth'),
                    'y':('year','years','yr','yrs'),
                }
                for key, words in unit_dict.iteritems():
                    if unit == key:
                        return number*unit_amounts[key]
                    for word in words:
                        if dl_distance(word, unit) <= 1:
                            return number*unit_amounts[key]
            
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
            if (lvalue == category.lower()) or (dl_distance(lvalue, word) <= 1):
                return category
    raise ValidationError("Expected a muac reading "
                "(\"green\", \"red\", \"yellow\" or a number), "
                "but received instead: %s." % value)
    

def parse_oedema(command, value):
    lvalue = value.lower().strip()
    if dl_distance(lvalue, 'oedema') <= 1:
        return 'T'
    else:
        return 'F'

def parse_facility_value(value):
    try:
        return HealthFacility.objects.get(code=value)
    except:
        raise ValidationError("Expected an HMIS facility code (got: %s)." % value)

def parse_facility(command, value):
    return parse_facility_value(value)

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

XFormField.register_field_type('facility', 'Facility Code', parse_facility,
                               db_type=XFormField.TYPE_OBJECT, xforms_type='string')

Poll.register_poll_type('facility', 'Facility Code Response', parse_facility_value, db_type=Attribute.TYPE_OBJECT, view_template='cvs/partials/response_facility_view.html',edit_template='cvs/partials/response_facility_edit.html',report_columns=(('Original Text', 'text'),('Health Facility','custom',),),edit_form=FacilityResponseForm)

def split_name(patient_name):
    names = patient_name.split(' ')
    first_name = names[0]
    last_name = ''
    middle_name = ''
    if len(names) > 1:
        last_name = names[len(names) - 1]
    if len(names) > 2:
        middle_name = ' '.join(names[1:-1])
    return (first_name, middle_name, last_name)

def get_or_create_patient(health_provider, patient_name, birthdate=None, deathdate=None, gender=None):
    for p in Patient.objects.filter(health_worker=health_provider):
        if dl_distance(p.full_name(), patient_name) <= 1:
            first_name, middle_name, last_name = split_name(patient_name)
            p.first_name = first_name
            p.middle_name = middle_name
            p.last_name = last_name
            if birthdate:
                p.birthdate = birthdate
            if deathdate:
                p.deathdate = deathdate
            if gender:
                p.gender = gender
            p.save()
            return p
    return create_patient(health_provider, patient_name, birthdate, deathdate, gender)

def create_patient(health_provider, patient_name, birthdate, deathdate, gender):
    first_name, middle_name, last_name = split_name(patient_name)

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
    patient.health_worker=health_provider
    patient.save()
    return patient

def check_validity(xform_type, submission, health_provider, patient, day_range):
    xform = XForm.objects.get(keyword=xform_type)
    start_date = datetime.datetime.now() - datetime.timedelta(hours=(day_range*24))
    for s in XFormSubmission.objects.filter(connection__contact__healthproviderbase__healthprovider=health_provider,
                                            xform=xform,
                                            created__gte=start_date,
                                            report__patient=patient).exclude(pk=submission.pk):
        pe = s.report
        pe.valid = False
        pe.save()
        s.has_errors = True
        s.save()
    return True

def check_basic_validity(xform_type, submission, health_provider, day_range):
    xform = XForm.objects.get(keyword=xform_type)
    start_date = datetime.datetime.now() - datetime.timedelta(hours=(day_range*24))
    for s in XFormSubmission.objects.filter(connection__contact__healthproviderbase__healthprovider=health_provider,
                                            xform=xform,
                                            created__gte=start_date).exclude(pk=submission.pk):
        s.has_errors = True
        s.save()

def patient_label(patient):
        gender = 'male' if patient.gender == 'M' else 'female'

        days = patient.age.days
        if days > 365:
            age_string = "aged %d" % (days // 365)
        elif days > 30:
            age_string = "(%d months old)" % (days // 30)
        else:
            age_string = "(infant)"

        return "%s, %s %s" % (patient.full_name(), gender, age_string)

def fix_location(sender, **kwargs):
    print "pre_delete on %s : %s" % (sender, str(kwargs['instance'].pk))
    if sender == Area:
        location = kwargs['instance']
        if location.parent:
            for c in HealthProvider.objects.filter(reporting_location = location):
                c.reporting_location = location.parent
                c.location = location.parent
                c.save()
            for h in HealthFacility.objects.filter(catchment_areas = location):
                h.catchment_areas.add(location.parent)
                h.save()

def xform_received_handler(sender, **kwargs):

    xform = kwargs['xform']
    submission = kwargs['submission']

    if submission.has_errors:
        return

    # TODO: check validity
    patient = None
    kwargs.setdefault('message', None)
    message = kwargs['message']
    try:
        message = message.db_message
        if not message:
            return
    except AttributeError:
        return

    if xform.keyword == 'reg':
        if submission.connection.contact:
            hp, created = HealthProvider.objects.get_or_create(pk=submission.connection.contact.pk)
        else:
            hp = HealthProvider.objects.create()
            conn = submission.connection
            conn.contact = hp
            conn.save()
        hp.name = submission.eav.reg_name
        hp.save()
        submission.response = "Thank you for registering, %s." % hp.name
        submission.save()
        return

    try:
        health_provider = submission.connection.contact.healthproviderbase.healthprovider
    except:
        submission.response = "Must be a reporter. Please register first with your name."
        submission.has_errors = True
        submission.save()
        return
    if xform.keyword == 'pvht':
        health_provider.groups.add(Group.objects.get(name='Peer Village Health Team'))
        health_provider.facility = submission.eav.pvht_facility
        health_provider.save()
        submission.response = "You have joined the system as Peer Village Health Team reporting to %s. " \
                   "Please resend if there is a mistake." % health_provider.facility.name
        submission.save()
        return
    if xform.keyword == 'vht':
        health_provider.groups.add(Group.objects.get(name='Village Health Team'))
        health_provider.facility = submission.eav.vht_facility
        health_provider.save()
        submission.response = "You have joined the system as Village Health Team reporting to %s." \
                   "Please resend if there is a mistake." % health_provider.facility.name
        submission.save()
        return
    if xform.keyword == 'muac':
        days = submission.eav.muac_age
        if not (submission.eav.muac_ignored == 'T'):
            submission.eav.muac_ignored = 'F'
            submission.save()
        birthdate = datetime.datetime.now() - datetime.timedelta(days=days)
        patient = get_or_create_patient(health_provider, submission.eav.muac_name, birthdate=birthdate, gender=submission.eav.muac_gender)
        check_validity(xform.keyword, submission, health_provider, patient, 1)
        report = PatientEncounter.objects.create(
                submission=submission,
                reporter=health_provider,
                patient=patient,
                message=message,
                valid=True)
        muac_label = "Severe Acute Malnutrition" if (submission.eav.muac_category == 'R') else "Risk of Malnutrition"
        submission.response = "%s has been identified with %s" % (patient_label(patient), muac_label)
        submission.save()
        return
    elif xform.keyword == 'birth':
        patient = get_or_create_patient(health_provider, submission.eav.birth_name, birthdate=datetime.datetime.now(), gender=submission.eav.birth_gender)
        check_validity(xform.keyword, submission, health_provider, patient, 3)
        report = PatientEncounter.objects.create(
                submission=submission,
                reporter=submission.connection.contact.healthproviderbase.healthprovider,
                patient=patient,
                message=message,
                valid=True)
        birth_location = "a facility" if submission.eav.birth_place == 'FACILITY' else 'home'
        submission.response = "Thank you for registering the birth of %s. We have recorded that the birth took place at %s." % (patient_label(patient), birth_location)
        submission.save()
        return
    elif xform.keyword == 'death':
        days = submission.eav.death_age
        birthdate = datetime.datetime.now() - datetime.timedelta(days=days)
        patient = get_or_create_patient(health_provider, submission.eav.death_name, birthdate=birthdate, gender=submission.eav.death_gender, deathdate=datetime.datetime.now())
        check_validity(xform.keyword, submission, health_provider, patient, 1)
        report = PatientEncounter.objects.create(
                submission=submission,
                reporter=health_provider,
                patient=patient,
                message=message,
                valid=True)
        submission.response = "We have recorded the death of %s." % patient_label(patient)
        submission.save()
        return
    elif xform.keyword == 'epi':
        check_basic_validity('epi', submission, health_provider, 1)
        value_list = []
        for v in submission.eav.get_values():
            value_list.append("%s %d" % (v.attribute.name, v.value_int))
        value_list[len(value_list) - 1] = " and %s" % value_list[len(value_list) - 1]
        submission.response = "You reported %s" % ','.join(value_list)
        submission.save()
        return
    elif xform.keyword == 'home':
        check_basic_validity('home', submission, health_provider, 1)
        value_list = []
        for v in submission.eav.get_values():
            value_list.append("%s %d" % (v.attribute.name, v.value_int))
        value_list[len(value_list) - 1] = " and %s" % value_list[len(value_list) - 1]
        submission.response = "You reported %s" % ','.join(value_list)
        submission.save()
        return


xform_received.connect(xform_received_handler, weak=True)
pre_delete.connect(fix_location, weak=True)