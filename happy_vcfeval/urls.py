from django.conf.urls import include, url
from django.contrib.auth import views as auth_views
from . import views

app_name = 'happy_vcfeval'
urlpatterns = [
    url(r'^$', views.upload, name="upload"),
    url(r'^processing/$', views.processing, name="processing"),
]
