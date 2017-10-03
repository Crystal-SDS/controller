from django.conf.urls import url
import views

urlpatterns = [

    url(r'^$', views.filter_list),
    url(r'^(?P<filter_id>\w+)/?$', views.filter_detail),
    url(r'^(?P<filter_id>\w+)/data/?$', views.FilterData.as_view()),

    # Deploy to project container or object
    url(r'^(?P<project_id>\w+)/deploy/(?P<filter_id>\w+)/?$', views.filter_deploy),
    url(r'^(?P<project_id>\w+)/(?P<container>[-\w]+)/deploy/(?P<filter_id>\w+)/?$', views.filter_deploy),
    url(r'^(?P<project_id>\w+)/(?P<container>[-\w]+)/(?P<swift_object>[-\w]+)/deploy/(?P<filter_id>\w+)/?$', views.filter_deploy),

    # Undeploy to project container or object
    url(r'^(?P<project_id>\w+)/undeploy/(?P<filter_id>\w+)/?$', views.filter_undeploy),
    url(r'^(?P<project_id>\w+)/(?P<container>[-\w]+)/undeploy/(?P<filter_id>\w+)/?$', views.filter_undeploy),
    url(r'^(?P<project_id>\w+)/(?P<container>[-\w]+)/(?P<swift_object>[-\w]+)/undeploy/(?P<filter_id>\w+)/?$', views.filter_undeploy),

    url(r'^dependencies/?$', views.dependency_list),
    url(r'^dependencies/(?P<dependency_id>\w+)/?$', views.dependency_detail),
    url(r'^dependencies/(?P<dependency_id>\w+)/data/?$', views.DependencyData.as_view()),
    url(r'^dependencies/(?P<project_id>\w+)/deploy/?$', views.dependency_list_deployed),
    url(r'^dependencies/(?P<project_id>\w+)/deploy/(?P<dependency_id>\w+)/?$', views.dependency_deploy),
    url(r'^dependencies/(?P<project_id>\w+)/undeploy/(?P<dependency_id>\w+)/?$', views.dependency_undeploy),

]
