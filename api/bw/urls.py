from django.conf.urls import url

import views

urlpatterns = [
    # url(r'^/slas/?$', views.bw_list),
    # # url(r'^/sla/(?P<project_key>[^/]+)/?$', views.bw_detail),
    # url(r'^/sla/(?P<dsl_filter>[^/]+)/(?P<slo_name>[^/]+)/(?P<target>[^/]+)/?$', views.bw_detail),

    # url(r'^/controllers/?$', views.bw_controller_list),
    # url(r'^/controllers/data/?$', views.ControllerData.as_view()),
    # url(r'^/controller/(?P<controller_id>\w+)/data/?$', views.ControllerData.as_view()),
    # url(r'^/controller/(?P<controller_id>\d+)/?$', views.bw_controller_detail)
]
