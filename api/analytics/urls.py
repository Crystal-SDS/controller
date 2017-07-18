from django.conf.urls import url

import views

urlpatterns = [

    url(r'^/analyzers/?$', views.analyzer_list),
    url(r'^/analyzers/data/?$', views.AnalyzerData.as_view()),
    url(r'^/analyzers/(?P<analyzer_id>\w+)/data/?$', views.AnalyzerData.as_view()),
    url(r'^/analyzers/(?P<analyzer_id>\d+)/?$', views.analyzer_detail),
    url(r'^/jobs/?$', views.job_history_list),
    url(r'^/jobs/data/?$', views.JobSubmitData.as_view()),

]