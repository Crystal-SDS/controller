from django.conf.urls import url

import views

urlpatterns = [

    url(r'^/metrics/?$', views.add_metric),
    url(r'^/metrics/(?P<name>\w+)/?$', views.metric_detail),

    url(r'^/metric_module/?$', views.metric_module_list),
    url(r'^/metric_module/data/?$', views.MetricModuleData.as_view()),
    url(r'^/metric_module/(?P<metric_module_id>\w+)/data/?$', views.MetricModuleData.as_view()),
    url(r'^/metric_module/(?P<metric_module_id>\w+)/?$', views.metric_module_detail),

    url(r'^/filters/?$', views.add_dynamic_filter),
    url(r'^/filters/(?P<name>\w+)/?$', views.dynamic_filter_detail),

    # TODO Change these to target groups (e.g. multiple containers)
    url(r'^/gtenants/?$', views.add_tenants_group),
    url(r'^/gtenants/(?P<gtenant_id>\w+)/?$', views.tenants_group_detail),
    url(r'^/gtenants/(?P<gtenant_id>\w+)/tenants/(?P<tenant_id>\w+)/?$', views.gtenants_tenant_detail),

    url(r'^/static_policy/?$', views.policy_list),
    url(r'^/static_policy/(?P<policy_id>[^/]+)/?$', views.static_policy_detail),

    url(r'^/dynamic_policy/?$', views.policy_list),
    url(r'^/dynamic_policy/(?P<policy_id>\w+)/?$', views.dynamic_policy_detail),

    url(r'^/snode/?$', views.list_storage_node),
    url(r'^/snode/(?P<snode_id>\w+)/?$', views.storage_node_detail),

    url(r'^/object_type/?$', views.object_type_list),
    url(r'^/object_type/(?P<object_type_name>\w+)/?$', views.object_type_detail),

    url(r'^/global_controllers/?$', views.global_controller_list),
    url(r'^/global_controllers/data/?$', views.GlobalControllerData.as_view()),
    url(r'^/global_controller/(?P<controller_id>\w+)/data/?$', views.GlobalControllerData.as_view()),
    url(r'^/global_controller/(?P<controller_id>\d+)/?$', views.global_controller_detail)

]
