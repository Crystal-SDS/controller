
from django.conf.urls import patterns, url

from . import views

urlpatterns = [
    url(r'^/?$', views.StorletList.as_view()),
    url(r'^/(?P<id>[0-9]+)/$', views.storlet_detail),
    url(r'^/(?P<id>[0-9]+)/data/$', views.StorletData.as_view()),
    url(r'^/(?P<account>\w+)/deploy/?$', views.storlet_list_deployed),
    url(r'^/(?P<account>\w+)/deploy/(?P<id>[0-9]+)$', views.storlet_deploy),
    url(r'^/(?P<account>\w+)/undeploy/(?P<id>[0-9]+)$', views.storlet_undeploy),


    url(r'^/dependencies/?$', views.dependency_list),
    url(r'^/dependencies/(?P<name>\w+)/$', views.dependency_detail),
    url(r'^/dependencies/(?P<name>\w+)/data/$', views.dependency_data),
    url(r'^/dependencies/(?P<account>\w+)/data/deploy/(?P<name>\w+)$', views.dependency_deploy),

]
