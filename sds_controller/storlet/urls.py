
from django.conf.urls import patterns, url

from . import views

urlpatterns = [
    url(r'^/?$', views.storlet_list),
    url(r'^/(?P<id>[0-9]+)/$', views.storlet_detail),
    url(r'^/(?P<id>[0-9]+)/data/$', views.storlet_data),
    url(r'^/(?P<id>[0-9]+)/deploy/$', views.storlet_deploy),

    url(r'^/dependencies/?$', views.dependency_list),
    url(r'^/dependencies/(?P<name>\w+)/$', views.dependency_detail),
    url(r'^/dependencies/(?P<name>\w+)/data/$', views.dependency_data),
    url(r'^/dependencies/(?P<name>\w+)/data/deploy$', views.dependency_deploy),

]
