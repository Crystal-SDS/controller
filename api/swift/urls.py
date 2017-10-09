from django.conf.urls import url
from . import views

urlpatterns = [
    # Storages Policies
    url(r'^storage_policies/?$', views.storage_policies),
    url(r'^storage_policy/(?P<storage_policy_id>[^/]+)/?$', views.storage_policy_detail),

    # Object Placement
    url(r'^locality/(?P<account>\w+)(?:/(?P<container>[-\w]+))(?:/(?P<swift_object>[-\w]+))?/$', views.locality_list),

    # url(r'^sort_nodes/?$', views.sort_list),
    # url(r'^sort_nodes/(?P<sort_id>[0-9]+)/?$', views.sort_detail),

    # Nodes
    url(r'^nodes/?$', views.node_list),
    url(r'^nodes/(?P<server_type>[^/]+)/(?P<node_id>[^/]+)/?$', views.node_detail),
    url(r'^nodes/(?P<server_type>[^/]+)/(?P<node_id>[^/]+)/restart/?$', views.node_restart),

    # Regions
    url(r'^regions/?$', views.regions),
    url(r'^regions/(?P<region_id>[^/]+)/?$', views.region_detail),
    url(r'^zones/?$', views.zones),
    url(r'^zones/(?P<zone_id>[^/]+)/?$', views.zone_detail),
    
]
