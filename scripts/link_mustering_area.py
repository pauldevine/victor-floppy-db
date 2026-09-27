#i used this script to initially take the meta data in the disk database I downloaded from the 
#internet archive and find the corresponding folder on the Mac disk. I assumed
#the filename on the local file system was the same as the title in the internet
#archive, this worked for about 50% of the entries
import os
import sys
from pathlib import Path
import json
import django
import internetarchive as ia
import dateparser
from django.core.files import File

# Get Django project path from environment or use relative path
PROJECT_PATH = os.environ.get('DJANGO_PROJECT_PATH', str(Path(__file__).parent.parent))
sys.path.insert(0, PROJECT_PATH)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "victordisk.settings")
django.setup()
mustering_dir = "/Users/pauldevine/Documents/Victor9k Stuff/Disk Mustering Area/"

from floppies.models import Entry, ArchCollection, Contributor, Creator, Language, Subject, Mediatype

def check_file_exists(directory, filename):
    if not isinstance(directory, str) or not isinstance(filename, str):
        raise ValueError("Both directory and filename must be strings")

    # Construct the full file path
    file_path = os.path.join(directory, filename)

    # Check if the file exists at the specified path
    return os.path.isdir(file_path)

def get_entries():
  entries = Entry.objects.all()
  for item in entries:
    exists = check_file_exists(mustering_dir, item.title)
    if exists:
        folder_path = os.path.join(mustering_dir, item.title)
        item.folder = folder_path
        item.save()
    print(item.title, exists)
  

print("Linking data to file system")
get_entries()
