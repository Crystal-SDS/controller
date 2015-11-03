from django.conf.urls import patterns, url

from . import views

urlpatterns = [
    url(r'^/metric/(?P<name>\w+)/?$', views.add_metric),
    url(r'^/filter/(?P<name>\w+)/?$', views.add_filter),
]
