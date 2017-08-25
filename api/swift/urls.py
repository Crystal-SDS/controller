from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^/tenants/?$', views.tenants_list),
    url(r'^/storage_policies/?$', views.storage_policy_list),
    url(r'^/spolicies/?$', views.storage_policies),
    url(r'^/locality/(?P<account>\w+)(?:/(?P<container>[-\w]+))(?:/(?P<swift_object>[-\w]+))?/$', views.locality_list),
    url(r'^/sort_nodes/?$', views.sort_list),
    url(r'^/sort_nodes/(?P<sort_id>[0-9]+)/?$', views.sort_detail),

    # Node status
    url(r'^/nodes/?$', views.node_list),
    url(r'^/nodes/(?P<server>[^/]+)/(?P<node_id>[^/]+)/?$', views.node_detail),
    url(r'^/nodes/(?P<node_id>[^/]+)/restart/?$', views.node_restart)
]
