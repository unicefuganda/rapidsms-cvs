from django.conf.urls.defaults import *
from cvs.views.stats import *
urlpatterns = patterns('',
 url(r'^cvs/stats/$', index),
        )