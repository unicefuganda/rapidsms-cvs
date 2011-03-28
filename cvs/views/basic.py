from django.template import RequestContext
from django.shortcuts import render_to_response
from rapidsms_xforms.models import XForm, XFormSubmission
from generic.views import generic
from generic.sorters import SimpleSorter
from cvs.sorters import SubmissionValueSorter
def index(request):
    return render_to_response("cvs/index.html", {}, RequestContext(request))

def view_submissions(req, form_id):
    xform = XForm.on_site.get(pk=form_id)

    submissions = xform.submissions.all().order_by('-pk')
    fields = xform.fields.all().order_by('pk')

    breadcrumbs = (('XForms', '/xforms/'),('Submissions', ''))
    columns = [('Type',False,'type',None), ('Date',True,'created',SimpleSorter())]
    for field in fields:
        columns.append((field.name.capitalize(), True,field.slug,SubmissionValueSorter()))

    return generic(req,
        model=XFormSubmission,
        queryset=xform.submissions.all(),
        sort_column='created',
        sort_ascending=False,
        objects_per_page=25,
        selectable=False,
        results_title=' %s Submissions' % xform.name.capitalize(),
        base_template='cvs/submissions_base.html',
        columns=columns,
        fields=fields,
        form=xform,
        partial_row='cvs/partials/submission_row.html',
    )

