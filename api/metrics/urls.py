from django.conf.urls import url
import views

urlpatterns = [

    # Metrics
    url(r'^activated/?$', views.list_activated_metrics),

    url(r'^$', views.metric_module_list),
    url(r'^data/?$', views.MetricModuleData.as_view()),
    url(r'^(?P<metric_module_id>\w+)/data/?$', views.MetricModuleData.as_view()),
    url(r'^(?P<metric_module_id>\w+)/?$', views.metric_module_detail),

]
