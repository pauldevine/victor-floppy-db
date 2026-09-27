#script to link a previously created csv with a mapping of identifiers to
#local macos directory location

import os
import sys
from pathlib import Path
import json
import django
import internetarchive as ia
import dateparser

# Get Django project path from environment or use relative path
PROJECT_PATH = os.environ.get('DJANGO_PROJECT_PATH', str(Path(__file__).parent.parent))
sys.path.insert(0, PROJECT_PATH)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "victordisk.settings")
django.setup()

import csv
from floppies.models import Entry, ArchCollection, Contributor, Creator, Language, Subject

csv_file_path = '/Users/pauldevine/projects/disk_db/disk db folder identifier.csv'

with open(csv_file_path, newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        identifier = row['identifier']
        folder = row['folder']
        
        # Update the database
        try:
            entry = Entry.objects.get(identifier=identifier)
            entry.folder = folder
            entry.save()
            print(f"Saved identifier {identifier}")
        except Entry.DoesNotExist:
            print(f"No entry found for identifier {identifier}")
