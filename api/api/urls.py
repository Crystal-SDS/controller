from django.conf.urls import include, url


urlpatterns = [
    url(r'^swift/', include('swift_api.urls')),
    url(r'^projects/', include('projects.urls')),
    url(r'^filters/', include('filters.urls')),
    url(r'^metrics/', include('metrics.urls')),
    url(r'^policies/', include('policies.urls')),
    url(r'^controllers/', include('controllers.urls')),
    url(r'^analytics/', include('analytics.urls')),
]
