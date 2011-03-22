from django import template
from django.shortcuts import get_object_or_404
from simple_locations.models import Area
from rapidsms_xforms.models import XFormSubmission
import datetime
from django.utils.safestring import mark_safe
import calendar
import time

def get_section(path):
    pos = path.split('/')
    return pos[2]

def get_parent(location_id):
    if location_id:
        location = get_object_or_404(Area, pk=location_id)
    else:
        location = Area.tree.root_nodes()[0]
    return location

def get_parentId(location_id):
    if location_id:
        location = get_object_or_404(Area, pk=location_id)
    else:
        location = Area.tree.root_nodes()[0]
    return location.parent_id

def get_ancestors(location_id):
    if location_id:
        location = get_object_or_404(Area, pk=location_id)
    else:
        location = Area.tree.root_nodes()[0]
    return location.get_ancestors()

def get_district(location):
    try:
        return location.get_ancestors().get(kind__name='district').name
    except:
        return None

def name(location):
    return location.name

def latest(obj):
    try:
        return XFormSubmission.objects.filter(connection__in=obj.connection_set.all()).latest('created').created
    except:
        return None

def hash(h, key):
    try:
        val =h[key]
    except KeyError:
        val=None
    return val
month_options = (
    (),
    (1, 'Jan'),
    (2, 'Feb'),
    (3, 'Mar'),
    (4, 'Apr'),
    (5, 'May'),
    (6, 'Jun'),
    (7, 'Jul'),
    (8, 'Aug'),
    (9, 'Sept'),
    (10, 'Oct'),
    (11, 'Nov'),
    (12, 'Dec'),
)

class DateRangeNode(template.Node):

    def __init__(self ,min_date,max_date,start_date, end_date):
        self.end_date = template.Variable(end_date)
        self.start_date = template.Variable(start_date)
        self.min_date = template.Variable(min_date)
        self.max_date=template.Variable(max_date)
    def render(self,context):
        try:
            end_date=self.end_date.resolve(context)
            start_date=self.start_date.resolve(context)
            min_date=self.min_date.resolve(context)
            max_date=self.max_date.resolve(context)
        except template.VariableDoesNotExist:
            return ''
        start_date=datetime.datetime.fromtimestamp(start_date/1000)
        end_date=datetime.datetime.fromtimestamp(end_date/1000)
        min_date=datetime.datetime.fromtimestamp(min_date/1000)
        max_date=datetime.datetime.fromtimestamp(max_date/1000)

        years = range(min_date.year, max_date.year + 1)
        start_opts = \
        """
            <label for='%s'>%s</label>
            <select name='%s' id='%s' style='display:none;'>"""
        for year in years:

            opt_year = "<optgroup label='%s'>" % str(year)
            start_opts = start_opts + opt_year
            if year==min_date.year:
                for month in range(min_date.month,13):
                    opt_month = "<optgroup label='%s'>" % str(month_options[month][1])
                    start_opts = start_opts + opt_month
                    for day in range(1,calendar.monthrange(year,month)[1]+1):
                        option = "<option value=%d>%s-%s-%s</option>"\
                     % (time.mktime(datetime.datetime(year,month,day).timetuple())*1000, str(day),str(month_options[month][1]),str(year))
                        start_opts = start_opts + option
                    start_opts = start_opts + '</optgroup>'


            elif year==max_date.year:
                for month in range(1,max_date.month+1):
                    opt_month = "<optgroup label='%s'>" % str(month_options[month][1])
                    start_opts = start_opts + opt_month
                    for day in range(1,calendar.monthrange(year,month)[1]+1):
                        option = "<option value=%d>%s-%s-%s</option>"\
                     % (time.mktime(datetime.datetime(year,month,day).timetuple())*1000, str(day),str(month_options[month][1]),str(year))
                        start_opts = start_opts + option
                    start_opts = start_opts + '</optgroup>'
            else:
                for month in range(1, 13):
                    opt_month = "<optgroup label='%s'>" % str(month_options[month][1])
                    start_opts = start_opts + opt_month
                    for day in range(1,calendar.monthrange(year,month)[1]+1):
                        option = "<option value=%d>%s-%s-%s</option>"\
                     % (time.mktime(datetime.datetime(year,month,day).timetuple())*1000, str(day),str(month_options[month][1]),str(year))
                        start_opts = start_opts + option
                    start_opts = start_opts + '</optgroup>'

            start_opts = start_opts + '</optgroup>'
        start_opts = start_opts + '</select>'
        js="""<script type="text/javascript>"$('select#start option[value=%d]').attr('selected','selected');
            $('select#end option[value=%d]').attr('selected','selected');
        </script>"""%(time.mktime(start_date.date().timetuple())*1000,time.mktime(end_date.date().timetuple())*1000)
        start_html = start_opts % ('start', '', 'start', 'start')
        end_html = start_opts % ('end', '', 'end', 'end')
        print start_html + end_html+js
        return mark_safe(start_html + end_html+js)




def do_date_range(parser, token):
	"""
	returns dateranges grouped by month and by week

	"""
	chunks = token.split_contents()
	if not len(chunks) == 5:
		raise template.TemplateSyntaxError, "%r tag requires two arguments" % token.contents.split()[0]

	return DateRangeNode(chunks[1],chunks[2],chunks[3],chunks[4])


register = template.Library()
register.filter('section', get_section)
register.filter('parent', get_parent)
register.filter('parentId', get_parentId)
register.filter('ancestors',get_ancestors)
register.filter('name', name)
register.filter('latest', latest)
register.filter('hash', hash)
register.filter('get_district', get_district)
register.tag('date_range',do_date_range)