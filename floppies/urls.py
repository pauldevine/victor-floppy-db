from django.urls import path
from . import views
from django.urls import include

from .views import EntryCreateView, EntryDeleteView, EntryUpdateView
from .models import Entry


app_name = "floppies"
urlpatterns = [
    path("", views.IndexView.as_view(), name="index"),
    path("floppies/<int:pk>/", views.DetailView.as_view(), name="entry-detail"),
    path("floppies/<int:pk>/results/", views.ResultsView.as_view(), name="results"),
    path("entries/add/", EntryCreateView.as_view(), name="entry-add"),
    path("entries/<int:pk>/", EntryUpdateView.as_view(), name="entry-update"),
    path("entries/<int:pk>/delete/", EntryDeleteView.as_view(), name="entry-delete"),
    path('ckeditor/', include('ckeditor_uploader.urls')),
]