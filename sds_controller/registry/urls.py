from django.conf.urls import url

from . import views

urlpatterns = [

    url(r'^/metrics/?$', views.add_metric),
    url(r'^/metrics/(?P<name>\w+)/?$', views.metric_detail),

    url(r'^/filters/?$', views.add_dynamic_filter),
    url(r'^/filters/(?P<name>\w+)/?$', views.dynamic_filter_detail),

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

    url(r'^/nodes/?$', views.node_list),

]
