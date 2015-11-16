from django.conf.urls import patterns, url

from . import views

urlpatterns = [

    url(r'^/metrics/?$', views.add_metric),
    url(r'^/metrics/(?P<id>\w+)/?$', views.metric_detail),

    url(r'^/filters/?$', views.add_dynamic_filter),
    url(r'^/filters/(?P<id>\w+)/?$', views.dynamic_filter_detail),

    url(r'^/gtenants/?$', views.add_tenants_group),
    url(r'^/gtenants/(?P<gtenant_id>\w+)/?$', views.tenants_group_detail),
    url(r'^/gtenants/(?P<gtenant_id>\w+)/tenants/(?P<tenant_id>\w+)/?$', views.gtenants_tenant_detail),

]
