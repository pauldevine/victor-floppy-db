#i used this script to initially take the meta data in the disk database I downloaded from the 
#internet archive and find the corresponding folder on the Mac disk. I assumed
#the filename on the local file system was the same as the title in the internet
#archive, this worked for about 50% of the entries
import os
import sys
import json
import django
import internetarchive as ia
import dateparser
from django.core.files import File
from pathlib import Path
import osxmetadata
import json 

import a2r_reader
import zip_contents
import disk_mustering as mustering

sys.path.insert(0, '/Users/pauldevine/projects/disk_db/victordisk')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "victordisk.settings")
django.setup()
mustering_dir = "/Users/pauldevine/Documents/Victor9k Stuff/Disk Mustering Area/"

from floppies.models import Entry, ArchCollection, Contributor, Creator, FluxFile, InfoChunk, Language, MetaChunk, PhotoImage, Subject, ZipArchive, ZipContent

def debug_print(folder_dict, message):
    print(message)
    folder_dict["debug_text"] += str(message)

def get_entry_folder(id):
    entry = Entry.objects.get(pk=id)

    exists = mustering.check_dir_exists(entry.folder)
    if not exists:
        print("Directory missing: {} {}".format(entry.id, entry.folder))
        return None
    if not zip_contents.has_zip_files(entry.folder):
        print("Directory missing zip file: {} {}".format(entry.id, entry.folder))
        return None
    return entry.folder

def update_entries():
    entries = Entry.objects.all()
    item = Entry.objects.get(pk=379)
    #for item in entries:
    folder_path = get_entry_folder(item.id) 
    details = mustering.get_file_details(folder_path, item.id)
    mustering.update_entry_details(details) 

# Main function
def main():
    print("Linking data to file system")
    update_entries()

if __name__ == "__main__":
    main()
