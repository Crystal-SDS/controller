
from django.conf.urls import patterns, url

from . import views

urlpatterns = [
    url(r'^storlets/$', views.storlet_list),
    url(r'^storlets/(?P<id>[0-9]+)/$', views.storlet_detail),
    url(r'^storlets/(?P<id>[0-9]+)/data/$', views.storlet_data),
    url(r'^storlets/(?P<id>[0-9]+)/deploy/$', views.storlet_deploy),

    url(r'^storlets/dependencies/$', views.dependency_list),
    url(r'^storlets/dependencies/(?P<id>[0-9]+)/$', views.dependency_detail),
    url(r'^storlets/dependencies/(?P<id>[0-9]+)/data/$', views.dependency_data),
    url(r'^storlets/dependencies/(?P<id>[0-9]+)/data/deploy$', views.dependency_deploy),

]
