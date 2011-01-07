from django.conf.urls.defaults import *
from cvs.views.stats import *
from cvs.views.chart import *
urlpatterns = patterns('',
   url(r'^cvs/stats/$', index),
   url(r'^cvs/stats/(\d+)/$', index),
   url(r'^cvs/stats/muac/$', muac),
   url(r'^cvs/stats/muac/(\d+)/$', muac),
   url(r'^cvs/stats/epi/$', epi),
   url(r'^cvs/stats/epi/(\d+)/$', epi),
   url(r'^cvs/charts/(?P<location_id>\d+)/(?P<xform_keyword>[a-z]+)/(?P<attribute_keyword>[a-zA-Z_]+)/(?P<attribute_value>[a-zA-Z_]+)/', chart),
   url(r'^cvs/charts/(?P<location_id>\d+)/(?P<xform_keyword>[a-z]+)/(?P<attribute_keyword>[a-z]+)/', chart),                       
   url(r'^cvs/charts/(?P<xform_keyword>[a-z]+)/(?P<attribute_keyword>[a-z]+)/', chart),
   url(r'^cvs/charts/(?P<xform_keyword>[a-z]+)', chart),
)