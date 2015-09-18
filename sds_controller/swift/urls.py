
from django.conf.urls import patterns, url

from . import views

urlpatterns = [
    url(r'^/tenants/?$', views.tenants_list),

]
