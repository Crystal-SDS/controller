
from django.conf.urls import patterns, url

from . import views

urlpatterns = [
    url(r'^/?$', views.bw_list),
    url(r'^/(?P<account>\w+)/$', views.bw_detail),

    url(r'^/clear/$', views.bw_clear_all),
    url(r'^/clear/(?P<account>\w+)/$', views.bw_clear_account),
    url(r'^/clear/(?P<account>\w+)/(?P<policy>\w+)/$', views.bw_clear_policy),

    url(r'^/(?P<account>\w+)/(?P<bw_value>[0-9]+)/$', views.bw_update),
    url(r'^/(?P<account>\w+)/(?P<policy>\w+)/(?P<bw_value>[0-9]+)/$', views.bw_update_policy),

    #Not implemented
    #url(r'^/osinfo/$', views.bw_delete),
    #url(r'^/osinfo/(?P<ip>)$', views.bw_delete),

]
