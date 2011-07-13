from rapidsms_xforms.models import XFormField, XForm, XFormSubmission, dl_distance, xform_received
import re
import datetime
from healthmodels.models import *
from healthmodels.models.HealthProvider import HealthProviderBase
from rapidsms.contrib.locations.models import Location
from django.core.exceptions import ValidationError
from django.contrib.auth.models import Group
from django.db.models.signals import pre_delete
from rapidsms.models import Contact
from poll.models import Poll
from eav.models import Attribute
from cvs.forms import FacilityResponseForm
from script.signals import *
from script.models import *
from uganda_commond import find_closest_match, find_best_response, parse_district_value
from rapidsms.contrib.locations.models import Location
import itertools

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

Poll.register_poll_type('facility', 'Facility Code Response', parse_facility_value, db_type=Attribute.TYPE_OBJECT, view_template='cvs/partials/response_facility_view.html',edit_template='cvs/partials/response_facility_edit.html',report_columns=(('Original Text', 'text'),('Health Facility','custom',),),edit_form='cvs.forms.FacilityResponseForm')

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

def generate_tracking_tag(start='2a2', base_numbers='2345679',
                          base_letters='acdefghjklmnprtuvwxy', **kwargs):
    """
        Generate a unique tag. The format is xyz[...] with x, y and z picked
        from an iterable giving a new set of ordered caracters at each
        call to next. You must pass the previous tag and a patter the tag
        should validate against.

        This is espacially usefull to get a unique tag to display on mobile
        device so you can exclude figures and letters that could be 
        confusing or hard to type.

        Default values are empirically proven to be easy to read and type
        on old phones.

        The code format alternate a char from base_number and base_letters,
        be sure the 'start' argument follows this convention or you'll
        get a ValueError.

        e.g:

        >>> generate_tracking_tag()
        '3a2'
        >>> generate_tracking_tag('3a2')
        '4a2'
        >>> generate_tracking_tag('9y9')
        '2a2a'
        >>> generate_tracking_tag('2a2a')
        '3a2a'
        >>> generate_tracking_tag('9a2a')
        '2c2a'

    """

    next_tag = []

    matrix_generator = itertools.cycle((base_numbers, base_letters))

    for index, c in enumerate(start):

        matrix = matrix_generator.next()

        try:
            i = matrix.index(c)
        except ValueError:
            raise ValueError(u"The 'start' argument must be correctly "\
                             u"formated. Check doctstring for more info.")

        try:
            next_char = matrix[i+1]
            next_tag.append(next_char)
            try:
                next_tag.extend(start[index+1:])
                break
            except IndexError:
                pass
        except IndexError:
            next_tag.append(matrix[0])
            try:
                start[index+1]
            except IndexError:
                matrix = matrix_generator.next()
                next_tag.append(matrix[0])
                break

    return ''.join(next_tag)

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
    if sender == Location:
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

    elif xform.keyword in ['com','mal','rutf','home','epi']:
        check_basic_validity(xform.keyword, submission, health_provider, 1)
        value_list = []
        for v in submission.eav.get_values():
            value_list.append("%s %d" % (v.attribute.name, v.value_int))
        value_list[len(value_list) - 1] = " and %s" % value_list[len(value_list) - 1]
        submission.response = "You reported %s.If there is an error,please resend." % ','.join(value_list)

        # aliasing for different epi commands
        if xform.keyword == 'epi':
            for v in submission.eav.get_values():
                if v.attribute.slug == 'epi_rb':
                    submission.eav.epi_ra = (submission.eav.epi_ra or 0) + v.value_int
                elif v.attribute.slug == 'epi_dy':
                    submission.eav.epi_bd = (submission.eav.epi_bd or 0) + v.value_int
        submission.save()

    if not (submission.connection.contact and submission.connection.contact.active):
        submission.has_errors = True
        submission.save()
        return

def cvs_autoreg(**kwargs):
    connection = kwargs['connection']
    progress = kwargs['sender']
    if not progress.script.slug == 'cvs_autoreg':
        return
    session = ScriptSession.objects.filter(script=progress.script, connection=connection).order_by('-end_time')[0]
    script = progress.script
    rolepoll = script.steps.get(order=0).poll
    namepoll = script.steps.get(order=1).poll
    districtpoll = script.steps.get(order=2).poll
    healthfacilitypoll = script.steps.get(order=3).poll
    villagepoll = script.steps.get(order=4).poll
    numberspoll = script.steps.get(order=5).poll

    if not connection.contact:
        connection.contact = Contact.objects.create()
        connection.save
    contact = connection.contact

    name = find_best_response(session, namepoll)
    if name:
        contact.name = name[:100]

    contact.reporting_location = find_best_response(session, districtpoll)

#    age = find_best_response(session, agepoll)
#    if age and age < 100:
#        contact.birthdate = datetime.datetime.now() - datetime.timedelta(days=(365*int(age)))

#    gresps = session.responses.filter(response__poll=genderpoll, response__has_errors=False).order_by('-response__date')
#    if gresps.count():
#        gender = gresps[0].response
#        if gender.categories.filter(category__name='male').count():
#            contact.gender = 'M'
#        else:
#            contact.gender = 'F'

    village = find_best_response(session, villagepoll)
    if village:
        contact.village = find_closest_match(village, Location.objects)

    group = find_best_response(session, youthgrouppoll)
    default_group = None
    if Group.objects.filter(name='Other uReporters').count():
        default_group = Group.objects.get(name='Other uReporters')
    if group:
        group = find_closest_match(group, Group.objects)
        if group:
            contact.groups.add(group)
        elif default_group:
            contact.groups.add(default_group)
    elif default_group:
        contact.groups.add(default_group)

    if not contact.name:
        contact.name = 'Anonymous User'
    contact.save()

script_progress_was_completed.connect(cvs_autoreg, weak=False)
xform_received.connect(xform_received_handler, weak=True)
pre_delete.connect(fix_location, weak=True)