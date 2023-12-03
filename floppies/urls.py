from django.urls import path
from . import views


urlpatterns = [
    path('floppies/', views.current_datetime, name='current_datetime'),
]