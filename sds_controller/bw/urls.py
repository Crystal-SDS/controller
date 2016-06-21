from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^/slas/?$', views.bw_list),
    url(r'^/sla/(?P<tenant_key>[^/]+)/?$', views.bw_detail),
]
