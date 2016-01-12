
from django.conf.urls import patterns, url

from . import views

urlpatterns = [
    url(r'^/tenants/?$', views.tenants_list),
    url(r'^/locality/(?P<account>\w+)(?:/(?P<container>\w+))(?:/(?P<swift_object>\w+))?/$', views.locality_list),
]
