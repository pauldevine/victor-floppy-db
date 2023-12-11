from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.urls import reverse_lazy
from django.views import generic
from django.core.paginator import Paginator
from django.views.generic import ListView
from django.db.models import Q

from django.utils import timezone
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
import datetime

from .models import Entry

class IndexView(generic.ListView):
    template_name = "index.html"
    context_object_name = "latest_entry_list"
    paginate_by = 25

    def get_queryset(self):
        """Return the last twenty-five published entries."""
        return Entry.objects.order_by("-publicationDate")

class DetailView(generic.DetailView):
    model = Entry
    fields = ["identifier", "fullArchivePath", "folder", "title", "creators",
        "collections", "contributors", "languages", "description", 
        "subjects", "photos", "randoFiles", "uploaded", "hasFluxFile", 
        "hasFileContents", "needsWork", "readyToUpload"]
    template_name = "entry_detail.html"


class ResultsView(generic.DetailView):
    model = Entry
    template_name = "results.html"

class EntryCreateView(generic.CreateView):
    model = Entry
    fields = ["identifier", "fullArchivePath", "folder", "title", "creators",
        "collections", "contributors", "languages", "description", 
        "subjects", "photos", "randoFiles", "uploaded", "hasFluxFile", 
        "hasFileContents", "needsWork", "readyToUpload"]
    template_name = "entry_form.html"


class EntryUpdateView(generic.UpdateView):
    model = Entry
    fields = ["identifier", "fullArchivePath", "folder", "title", "creators",
        "collections", "contributors", "languages", "description", 
        "subjects", "photos", "randoFiles", "uploaded", "hasFluxFile", 
        "hasFileContents", "needsWork", "readyToUpload"]
    template_name = "entry_form.html"


class EntryDeleteView(generic.DeleteView):
    model = Entry
    success_url = reverse_lazy("floppies-list")

class SearchResultsView(ListView):
    model = Entry
    template_name = 'search_results.html'

    def get_queryset(self): # new
        query = self.request.GET.get("q")
        if query is None:
            query = ""
        object_list = Entry.objects.filter(
            Q(title__icontains=query) | Q(identifier__icontains=query)
        )
        return object_list