from django import forms
from .models import Entry
from ckeditor.widgets import CKEditorWidget

class EntryForm(forms.ModelForm):
    description = forms.CharField(widget=CKEditorWidget())
    class Meta:
        model = Entry
        fields = '__all__'  # Includes all fields from the Entry model
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'created_on': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            # Add any other specific widgets if required    
            "description": CKEditorWidget(),
        }

