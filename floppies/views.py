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

from .models import Entry, ZipContent, ZipArchive

class IndexView(generic.ListView):
    template_name = "index.html"
    context_object_name = "latest_entry_list"
    paginate_by = 25

    def get_queryset(self):
        """Return the last twenty-five published entries."""
        needsWork = self.request.GET.get('needswork')
        nextUpload = self.request.GET.get('nextupload')
        queryset = Entry.objects.order_by("-modified_date")
        if needsWork:
            queryset = queryset.filter(needsWork=True)
        if nextUpload:
            queryset = queryset.filter(needsWork=False, readyToUpload=True, uploaded=False)
        return queryset

class DetailView(generic.DetailView):
    model = Entry
    fields = ["identifier", "fullArchivePath", "folder", "title", "creators",
        "collections", "contributors", "languages", "description", 
        "subjects", "photos", "randoFile", "uploaded", "hasFluxFile", 
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
        "subjects", "mediatype", "uploaded", "hasFluxFile", 
        "hasFileContents", "needsWork", "readyToUpload"]
    template_name = "entry_form.html"

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)

        # Get the Entry instance being updated
        entry = self.object

        zip_contents = []
        entry.ziparchives.all()
        
        # for zip_content in ZipContent.objects.filter(zipArchive__in=entry.zipArchives.all()):
        #     # Fetch related FluxFile objects for this ZipContent
        #     flux_files = list(zip_content.fluxes.all())

        #     # Create a dictionary to store zip_content and its related objects
        #     zip_content_data = {
        #         'zip_content': zip_content,
        #         'flux_files': flux_files,
        #         'info_chunks': [flux_file.info for flux_file in flux_files if flux_file.info],
        #         'meta_chunks': [flux_file.meta for flux_file in flux_files if flux_file.meta]
        #     }

        #     zip_contents.append(zip_content_data)

        # context["zip_contents"] = zip_contents
        return context



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