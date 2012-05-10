import os
from django.http import HttpResponse, HttpResponseBadRequest
from django.http import Http404
from django.conf import settings
from django.core.management import call_command

def save_upload(uploaded, filename, raw_data):
    '''
        raw_data: if True, uploaded is an HttpRequest object with the file being
        the raw post data
        if False, uploaded has been submitted via the basic form
        submission and is a regular Django UploadedFile in request.FILES
    '''
    try:
        from io import FileIO, BufferedWriter
        with BufferedWriter(FileIO(filename, "wb")) as dest:
            # if the "advanced" upload, read directly from the HTTP request
            # with the Django 1.3 functionality
            if raw_data:
                foo = uploaded.read(1024)
                while foo:
                    dest.write(foo)
                    foo = uploaded.read(1024)
            # if not raw, it was a form upload so read in the normal Django chunks fashion
            else:
                for c in uploaded.chunks():
                    dest.write(c)
            # got through saving the upload, report success
            return True
    except IOError:
        # could not open the file most likely
        pass
    return False


def ajax_upload(request):
    if request.method == "POST":
        if request.is_ajax():
            # the file is stored raw in the request
            print "stored raw in request"
            upload = request
            is_raw = True
            # AJAX Upload will pass the filename in the querystring if it is the "advanced" ajax upload
            try:
                filename = request.GET[ 'qqfile' ]
            except KeyError:
                return HttpResponseBadRequest("AJAX request not valid")
        # not an ajax upload, so it was the "basic" iframe version with submission via form
        else:
            is_raw = False
            if len(request.FILES) == 1:
                # FILES is a dictionary in Django but Ajax Upload gives the uploaded file an
                # ID based on a random number, so it cannot be guessed here in the code.
                # Rather than editing Ajax Upload to pass the ID in the querystring,
                # observer that each upload is a separate request,
                # so FILES should only have one entry.
                # Thus, we can just grab the first (and only) value in the dict.
                upload = request.FILES.values()[ 0 ]
            else:
                raise Http404("Bad Upload")
            filename = upload.name

        # save the file
        filename = "/tmp/%s" % filename
        success = save_upload(upload, filename, is_raw)
        call_command("load_reporters", filename)
        # let Ajax Upload know whether we saved it or not
        import json
        ret_json = { 'success': success, }
        return HttpResponse(json.dumps(ret_json))
