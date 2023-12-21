from django.contrib import admin

# Register your models here.

from .models import Entry, Creator, ArchCollection, Contributor, FluxFile, Language, \
                    PhotoImage, RandoFile, Subject, ZipArchive, ZipContent, ImportRun, \
                    InfoChunk, MetaChunk

admin.site.register(Entry)
admin.site.register(Creator)
admin.site.register(ArchCollection)
admin.site.register(Contributor)
admin.site.register(FluxFile)
admin.site.register(Language)
admin.site.register(PhotoImage)
admin.site.register(RandoFile)
admin.site.register(Subject)
admin.site.register(ZipArchive)
admin.site.register(ZipContent)
admin.site.register(ImportRun)
admin.site.register(InfoChunk)
admin.site.register(MetaChunk)