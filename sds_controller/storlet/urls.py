
from django.conf.urls import patterns, url

from . import views

urlpatterns = [
    url(r'^storlets/$', views.storlet_list),
    url(r'^storlets/(?P<id>[0-9]+)/$', views.storlet_detail),
]
