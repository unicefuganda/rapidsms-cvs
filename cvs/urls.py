from django.conf.urls.defaults import *
from cvs.views.stats import *
from cvs.views.chart import *
urlpatterns = patterns('',
   url(r'^cvs/stats/$', index,name='stats'),
   url(r'^cvs/stats/(?P<location_id>\d+)/$', index),
   url(r'^cvs/muac/$', muac_detail),
   url(r'^cvs/muac/(?P<location_id>\d+)/$', muac_detail),
   url(r'^cvs/epi/$', epi_detail),
   url(r'^cvs/epi/(?P<location_id>\d+)/$', epi_detail),
   url(r'^cvs/birth/$', birth_detail),
   url(r'^cvs/birth/(?P<location_id>\d+)/$', birth_detail),
   url(r'^cvs/death/$', death_detail),
   url(r'^cvs/death/(?P<location_id>\d+)/$', death_detail),
   url(r'^cvs/charts/(?P<location_id>\d+)/(?P<xform_keyword>[a-z]+)/(?P<attribute_keyword>[a-zA-Z_]+)/(?P<attribute_value>[0-9a-zA-Z_]+)/', chart),
   url(r'^cvs/charts/(?P<location_id>\d+)/(?P<xform_keyword>[a-z]+)/(?P<attribute_keyword>[a-z]+)/', chart),                       
   url(r'^cvs/charts/(?P<location_id>\d+)/(?P<xform_keyword>[a-z]+)/(?P<attribute_keyword>[a-z]+)/', chart),
   url(r'^cvs/charts/(?P<location_id>\d+)/(?P<xform_keyword>[a-z]+)/',chart),
   url(r'^cvs/charts/(?P<xform_keyword>[a-z]+)/(?P<attribute_keyword>[a-z]+)/', chart),
   url(r'^cvs/charts/(?P<xform_keyword>[a-z]+)', chart),
)