from django.conf.urls import url

from . import views

app_name = 'polls'
urlpatterns = [
    url(r'^$', views.IndexView.as_view(), name='index'),
    url(r'^(?P<pk>[0-9]+)/$', views.DetailView.as_view(), name='detail'),
    url(r'^(?P<pk>[0-9]+)/results/$', views.ResultsView.as_view(), name='results'),
    url(r'^(?P<question_id>[0-9]+)/vote/$', views.vote, name='vote'),
    url(r'^submit/$', views.submit, name='submit'),
    url(r'^login/$', views.LoginView.as_view(), name='login'),
    url(r'^check/$', views.check, name='check'),
    url(r'^upload/$', views.word_upload, name='upload'),
    url(r'^export/$', views.export_view, name='export'),
    url(r'^redo/$', views.redo, name='redo'),
]
