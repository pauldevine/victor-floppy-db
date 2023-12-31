#script to iterate through a folder in the filesystem and create an entry 
#into the disk database for each subfolder. The folder name becomes the title
#any readme or diskid becomes the description
import os
from pathlib import Path
import sys
import json
import django
import internetarchive as ia
import dateparser
import pathlib
from operator import itemgetter
import re
from datetime import datetime, timedelta
import argparse
import zipfile
import hashlib
from osxmetadata import OSXMetaData

import a2r_reader
import zip_contents
import disk_mustering as mustering
from disk_mustering import debug_print

sys.path.insert(0, '/Users/pauldevine/projects/disk_db/victordisk')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "victordisk.settings")
django.setup()

from floppies.models import Entry, ArchCollection, Contributor, Creator, FluxFile, InfoChunk
from floppies.models import Language, MetaChunk, Subject, PhotoImage, RandoFile, ZipArchive, ZipContent, ScriptRun

def insert_into_db(folder):
    debug_print(folder, "Inserting into disk_db identifier: {} folder_name{}".format(
        folder['identifier'], folder['folder_name']))
    debug_print(folder, "Folder {}".format(str(folder)))

    if 'description_file_contents' in folder:
        mydescription = folder['description_file_contents']
    else:
        mydescription = None

    entry = Entry(
        identifier = folder['identifier'],
        fullArchivePath = "https://archive.org/details/{}".format(folder['identifier']),
        folder = folder['folder_path'],
        title = folder['folder_name'],
        uploaded = False,
        needsWork = True,
        hasFluxFile = folder['hasFluxFile'],
        hasFileContents = folder['hasFileContents'],
        mediatype = 'SW',
        hasDiskImg = folder['hasDiskImgFile'],
        description = mydescription
    )
    entry.save()
    folder["id"]=entry.pk

    importRun = ScriptRun(
        entry = entry,
        text = folder['debug_text'],
        parentPath = folder['parent_path'],
        script = "create_records_from_diskmustering.py",
        function = "insert_into_db",
    )
    importRun.save()

    return

# Main function remains the same
def main():
    parser = argparse.ArgumentParser(description='Iterates through a local folder and extracts internet archive meta data for django.')
    parser.add_argument('src_dir', type=str, help='Looks in the source directory for folders tagged Yellow in Macos')
    args = parser.parse_args()
    parent_path = args.src_dir
    print("Reading folder contents from " + parent_path + " with a Yellow finder tag into disk database.")

    # Generate the sorted output
    folder_list = []
    tag_name = "Yellow"

    #returns a list of folders that are tagged yellow in the macos finder
    files_with_tag = mustering.get_files_with_tag_in_folder(tag_name, parent_path)

    # Iterate through each folder in the parent directory
    folder_list = []
    for folder_name in files_with_tag:
        details = mustering.get_file_details(folder_name, None) 
        insert_into_db(details)
        mustering.update_entry_details(details)
        folder_list.append(folder_name)
        
    print("Folder list:")
    for folder in folder_list:
        print("    ", folder)
    print("Finished inserting records, {} folders processed".format(len(folder_list)))
    return

if __name__ == "__main__":
    main()
