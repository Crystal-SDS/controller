from django.conf.urls import include, url


urlpatterns = [
    url(r'^swift/', include('swift.urls')),
    url(r'^projects/', include('projects.urls')),
    url(r'^filters/', include('filters.urls')),
    url(r'^metrics/', include('metrics.urls')),
    url(r'^policies/', include('policies.urls')),
<<<<<<< HEAD
    url(r'^controller/', include('controller.urls')),
    url(r'^analytics/', include('analytics.urls')),
=======
    url(r'^controllers/', include('controllers.urls')),
>>>>>>> refs/heads/dev
]
