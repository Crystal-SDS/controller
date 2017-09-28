from django.conf.urls import url
import views

urlpatterns = [

    # Global Controllers
    url(r'^global_controllers/?$', views.global_controller_list),
    url(r'^global_controllers/data/?$', views.GlobalControllerData.as_view()),
    url(r'^global_controller/(?P<controller_id>\w+)/data/?$', views.GlobalControllerData.as_view()),
    url(r'^global_controller/(?P<controller_id>\d+)/?$', views.global_controller_detail)

]
