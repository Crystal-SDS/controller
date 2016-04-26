from django.conf.urls import url

from . import views

urlpatterns = [
    # url(r'^/?$', views.bw_list),

    # url(r'^/clear/$', views.bw_clear_all),
    # url(r'^/osinfo/$', views.osinfo),
    #
    # url(r'^/(?P<account>\w+)/$', views.bw_detail),
    #
    # url(r'^/clear/(?P<account>\w+)/$', views.bw_clear_account),
    # url(r'^/clear/(?P<account>\w+)/(?P<policy>\w+)/$', views.bw_clear_policy),
    #
    # url(r'^/(?P<account>\w+)/(?P<bw_value>[0-9]+)/$', views.bw_update),
    # url(r'^/(?P<account>\w+)/(?P<policy>\w+)/(?P<bw_value>[0-9]+)/$', views.bw_update_policy),

    url(r'^/slas/?$', views.bw_list),
    url(r'^/sla/(?P<id>[0-9]+)/?$', views.bw_detail),

    # Not implemented
    # url(r'^/osinfo/(?P<ip>)$', views.bw_delete),

]
