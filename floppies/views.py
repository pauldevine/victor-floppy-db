from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.urls import reverse_lazy
from django.views import generic
from django.core.paginator import Paginator
from django.views.generic import ListView
from django.db.models import Q
from django.conf import settings

from django.utils import timezone
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
import datetime
from pathlib import Path

from .models import Entry, ZipContent, ZipArchive

DISK_MUSTERING_DIR = settings.DISK_MUSTERING_DIR

class IndexView(generic.ListView):
    template_name = "index.html"
    context_object_name = "latest_entry_list"
    paginate_by = 25

    def get_queryset(self):
        """Return the last twenty-five published entries."""
        needsWork = self.request.GET.get('needswork')
        nextUpload = self.request.GET.get('nextupload')
        dateOrder = self.request.GET.get('dateorder')
        if dateOrder:
            queryset = Entry.objects.order_by("-modified_date")
        else:
            queryset = Entry.objects.order_by("title")
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
        # Fix N+1 query problem: prefetch related data
        zip_archives = entry.ziparchives.prefetch_related(
            'zipcontent_set__fluxfile__metachunk',
            'zipcontent_set__fluxfile__infochunk',
            'zipcontent_set__textfile'
        ).all()

        # Preparing the context
        context['entry'] = entry
        context['zip_archives'] = []

        for zip_archive in zip_archives:
            path = Path(zip_archive.archive)
            try:
                relative_path = path.relative_to(DISK_MUSTERING_DIR)
            except ValueError:
                # If path is not relative to DISK_MUSTERING_DIR, use full path
                relative_path = path
            styled_path = str(relative_path).replace('/', '<span class="path-separator">/</span>')
            zip_archive_dict = {
                 'archive': zip_archive,
                 'zip_path': relative_path,
                 'zip_path_styled': styled_path,
                 'zip_contents': []}
            zip_contents = zip_archive.zipcontent_set.all()

            for zip_content in zip_contents:
                zip_content_dict = {'zip_content': zip_content}
                zip_content_dict['size_kb'] = int(zip_content.size_bytes / 1024) + (zip_content.size_bytes % 1024 > 0) if zip_content.size_bytes else 0

                # Only fetch FluxFile and MetaChunk for .a2r or .flux files
                if zip_content.suffix in ['.a2r', '.flux']:
                    flux_file = zip_content.fluxfile if hasattr(zip_content, 'fluxfile') else None
                    meta_chunk = flux_file.metachunk if flux_file and hasattr(flux_file, 'metachunk') else None
                    zip_content_dict['flux_file'] = flux_file
                    zip_content_dict['meta_chunk'] = meta_chunk
                else:
                    zip_content_dict['flux_file'] = None
                    zip_content_dict['meta_chunk'] = None
                file_desc = zip_content.textfile if hasattr(zip_content, 'textfile') else None
                zip_content_dict['file_desc'] = file_desc

                zip_archive_dict['zip_contents'].append(zip_content_dict)

            context['zip_archives'].append(zip_archive_dict)

        # Pass the context to your template
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