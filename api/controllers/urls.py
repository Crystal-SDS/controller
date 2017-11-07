from django.conf.urls import url
import views

urlpatterns = [

    # Controllers
    url(r'^$', views.controller_list),
    url(r'^data/?$', views.ControllerData.as_view()),
    url(r'^(?P<controller_id>\w+)/data/?$', views.ControllerData.as_view()),
    url(r'^(?P<controller_id>\d+)/?$', views.controller_detail),

    # Controller Instances
    url(r'^instances/?$', views.instances_list),
    url(r'^instance/?$', views.create_instance),
    url(r'^instance/(?P<instance_id>\w+)/?$', views.instance_detail),

]
