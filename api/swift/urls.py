from django.conf.urls import url
from . import views

urlpatterns = [
    # Storages Policies
    url(r'^storage_policies/?$', views.storage_policy_list),
    url(r'^storage_policies/?$', views.storage_policies),

    # Object Placement
    url(r'^locality/(?P<account>\w+)(?:/(?P<container>[-\w]+))(?:/(?P<swift_object>[-\w]+))?/$', views.locality_list),

    # url(r'^sort_nodes/?$', views.sort_list),
    # url(r'^sort_nodes/(?P<sort_id>[0-9]+)/?$', views.sort_detail),

    # Nodes
    url(r'^nodes/?$', views.node_list),
    url(r'^nodes/(?P<server_type>[^/]+)/(?P<node_id>[^/]+)/?$', views.node_detail),
    url(r'^nodes/(?P<server_type>[^/]+)/(?P<node_id>[^/]+)/restart/?$', views.node_restart)
]
