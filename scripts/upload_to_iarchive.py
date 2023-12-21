import os
import sys
import django
import internetarchive as ia
import subprocess
import json
from osxmetadata import OSXMetaData

sys.path.insert(0, '/Users/pauldevine/projects/disk_db/victordisk')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "victordisk.settings")
django.setup()

DISK_MUSTERING_DIR = "/Users/pauldevine/Documents/Victor9k Stuff/Disk Mustering Area/"


from floppies.models import Entry, Creator, Contributor, Language, Subject


def upload_entry_to_internet_archive(entry):
    # Prepare metadata
    metadata = {
        'title': entry.title,
        'mediatype': entry.get_mediatype_display(),  # Get display value of mediatype
        'description': entry.description,
        'creator': [creator.name for creator in entry.creators.all()],
        'contributor': [contributor.name for contributor in entry.contributors.all()],
        'language': [language.name for language in entry.languages.all()],
        'subject': [subject.name for subject in entry.subjects.all()],
        'date': entry.publicationDate.strftime("%Y-%m-%d") if entry.publicationDate else None,
        'collection': [collection.name for collection in entry.collections.all()],
        # Add other fields as necessary
    }

    # Get media files
    files = entry.get_media_files()  

    # Upload to Internet Archive
    item = ia.upload(entry.identifier, files, metadata=metadata)
    print(f"Uploaded {entry.title} with identifier {entry.identifier} item {item}")

    # Update the uploaded flag in your Django model
    entry.uploaded = True
    entry.save()

def upload_new_entries():
    new_entries = Entry.objects.filter(uploaded=False, readyToUpload=True)  # Adjust filter as necessary
    count = new_entries.count()
    print(f"Uploading {count} new entries.")
    for entry in new_entries:
        print(f"Starting {entry.identifier}.")
        upload_entry_to_internet_archive(entry)
        

# Main function remains the same
def main():

	upload_new_entries()

if __name__ == "__main__":
    main()
