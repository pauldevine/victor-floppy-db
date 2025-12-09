from django import forms
from .models import Entry
from ckeditor.widgets import CKEditorWidget

class EntryForm(forms.ModelForm):
    description = forms.CharField(widget=CKEditorWidget(), required=False)

    class Meta:
        model = Entry
        # Only expose fields that should be user-editable
        # Exclude internal/system fields: created_date, modified_date, uploaded
        fields = [
            'identifier',
            'title',
            'folder',
            'fullArchivePath',
            'publicationDate',
            'description',
            'mediatype',
            'creators',
            'collections',
            'contributors',
            'languages',
            'subjects',
            'needsWork',
            'readyToUpload',
            'hasFluxFile',
            'hasFileContents',
            'hasDiskImg',
        ]
        widgets = {
            'publicationDate': forms.DateInput(attrs={'type': 'date'}),
            'description': CKEditorWidget(),
        }

