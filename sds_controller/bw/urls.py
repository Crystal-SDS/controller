
from django.conf.urls import patterns, url

from . import views

urlpatterns = [
    url(r'^bw/$', views.bw_list),
    url(r'^bw/(?P<account>)/$', views.bw_detail),

    url(r'^bw/clear/$', views.bw_delete),
    url(r'^bw/clear/(?P<account>)/$', views.bw_delete),
    url(r'^bw/clear/(?P<account>)/(?P<policy>)/$', views.bw_delete),

    url(r'^bw/(?P<account>)/(?P<bw_value>[0-9]+)/$', views.bw_update),
    url(r'^bw/(?P<account>)/(?P<policy>)/(?P<bw_value>[0-9]+)/$', views.bw_update),

    url(r'^bw/osinfo/$', views.bw_delete),
    url(r'^bw/osinfo/(?P<ip>)$', views.bw_delete),

]
