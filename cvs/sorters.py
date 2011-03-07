from generic.sorters import Sorter
from rapidsms.models import Connection
from rapidsms_xforms.models import XFormSubmission

class LatestSubmissionSorter(Sorter):
    def sort(self, column, object_list, ascending=True):
        connections = list(Connection.objects.filter(contact__in=object_list))
        submissions = list(XFormSubmission.objects.filter(connection__in=connections).order_by('-created').select_related('connection__contact__healthproviderbase__facility','connection__contact__healthproviderbase__location'))
        full_contact_list = list(object_list)
        toret = []
        for sub in submissions:
            if not (sub.connection.contact.healthproviderbase in toret):
                toret.append(sub.connection.contact.healthproviderbase)
        nosubmissions = []
        for c in full_contact_list:
            if not (c in toret):
                nosubmissions.append(c)

        toret = toret + nosubmissions
        if not ascending:
            toret.reverse()
        return toret