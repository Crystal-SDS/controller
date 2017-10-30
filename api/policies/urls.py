from django.conf.urls import url
import views

urlpatterns = [

    # Static policies
    url(r'^static/?$', views.policy_list),
    url(r'^static/(?P<policy_id>[^/]+)/?$', views.static_policy_detail),

    # Dynamic policies
    url(r'^dynamic/?$', views.policy_list),
    url(r'^dynamic/(?P<policy_id>\w+)/?$', views.dynamic_policy_detail),

    # Access control
    url(r'^acl/?$', views.access_control),
    url(r'^acl/(?P<policy_id>[^/]+)/?$', views.access_control_detail),

    # Object Types
    url(r'^object_type/?$', views.object_type_list),
    url(r'^object_type/(?P<object_type_name>\w+)/?$', views.object_type_detail),

    # SLO'S
    url(r'^slos/?$', views.slo_list),
    url(r'^slo/(?P<dsl_filter>[^/]+)/(?P<slo_name>[^/]+)/(?P<target>[^/]+)/?$', views.slo_detail)
]
