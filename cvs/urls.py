from django.conf.urls.defaults import *
from cvs.views.stats import *
from cvs.views.chart import *
urlpatterns = patterns('',
   url(r'^cvs/stats/$', index,name='stats'),
   url(r'^cvs/muac/$', muac_detail),
   url(r'^cvs/epi/$', epi_detail),
   url(r'^cvs/death/$', death_detail),
   url(r'^cvs/home/$', home_detail),
   url(r'^cvs/birth/$', birth_detail),
   url(r'^cvs/stats/$', index),
   url(r'^cvs/stats/(?P<location_id>\d+)/$', index),
   url(r'^cvs/charts/(?P<location_id>\d+)/(?P<xform_keyword>[a-z]+)/(?P<attribute_keyword>[a-z]+)/', chart),
   url(r'^cvs/charts/(?P<location_id>\d+)/(?P<xform_keyword>[a-z]+)/',chart),
   url(r'^cvs/charts/(?P<xform_keyword>[a-z]+)/(?P<attribute_keyword>[a-z]+)/', chart),
   url(r'^cvs/charts/(?P<xform_keyword>[a-z]+)', chart),
)