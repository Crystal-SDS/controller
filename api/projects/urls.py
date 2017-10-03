from django.conf.urls import url
import views

urlpatterns = [

    # Crystal Project Groups
    url(r'^groups/?$', views.add_projects_group),
    url(r'^groups/(?P<group_id>\w+)/?$', views.projects_group_detail),
    url(r'^groups/(?P<group_id>\w+)/projects/(?P<project_id>\w+)/?$', views.projects_groups_detail),

    # Crystal Projects
    url(r'^$', views.projects),
    url(r'^(?P<project_id>\w+)/?$', views.projects),

]
