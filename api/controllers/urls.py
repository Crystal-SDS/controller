from django.conf.urls import url
import views

urlpatterns = [

    # Global Controllers
    url(r'^$', views.controller_list),
    url(r'^data/?$', views.ControllerData.as_view()),
    url(r'^(?P<controller_id>\w+)/data/?$', views.ControllerData.as_view()),
    url(r'^(?P<controller_id>\d+)/?$', views.controller_detail)

]
