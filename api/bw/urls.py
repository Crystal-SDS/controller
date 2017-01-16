from django.conf.urls import url

import views

urlpatterns = [
    url(r'^/slas/?$', views.bw_list),
    url(r'^/sla/(?P<project_key>[^/]+)/?$', views.bw_detail),

    url(r'^/controllers/?$', views.bw_controller_list),
    url(r'^/controller/(?P<controller_id>\d+)/?$', views.bw_controller_detail)
]
