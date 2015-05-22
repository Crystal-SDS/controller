
from django.conf.urls import patterns, url

from . import views

urlpatterns = [
    url(r'^list/$', views.storlet_list),
    url(r'^create/$', views.storlet_create),
]
