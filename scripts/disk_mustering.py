#this is a common library of methods to work with the disk mustering directory
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

# Make macOS metadata optional (only available on macOS)
try:
    from osxmetadata import OSXMetaData
    HAS_OSX_METADATA = True
except ImportError:
    HAS_OSX_METADATA = False
    print("Warning: osxmetadata not available. macOS Finder tag features will be disabled.")

import a2r_reader
import zip_contents

# Get Django project path from environment or use relative path
PROJECT_PATH = os.environ.get('DJANGO_PROJECT_PATH', str(Path(__file__).parent.parent))
sys.path.insert(0, PROJECT_PATH)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "victordisk.settings")
django.setup()

from django.conf import settings
from floppies.models import Entry, ArchCollection, Contributor, Creator, FluxFile, InfoChunk, Language, MetaChunk, PhotoImage, Subject, TextFile, ZipArchive, ZipContent

# Use configurable path from settings
DISK_MUSTERING_DIR = settings.DISK_MUSTERING_DIR
IMG_SUFFIXES = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']

def debug_print(folder_dict, message):
    print(message)
    folder_dict["debug_text"] += str(message)

def check_dir_exists(directory):
    #if we get a string cast to Path
    if isinstance(directory, str):
        directory = Path(directory)

    # Check if the file exists at the specified path
    return os.path.isdir(directory)

def get_files_from_dir(parent_path):
    # List all files in the sub-directory
    file_list = []
    for file_name in os.listdir(parent_path):
        # Ignore hidden files
        if file_name.startswith('.'):
            continue
        file_path = os.path.join(parent_path, file_name)
        file_list.append(file_path)

        #check if we're a directory, recurse there too
        if os.path.isdir(file_path):
            # Fixed: was missing assignment operator
            file_list.extend(get_files_from_dir(file_path))

    return file_list

def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_files_with_tag_in_folder(tag_name, folder_path):
    """
    Get files with a specific macOS Finder tag.
    Returns empty list if OSXMetaData is not available.
    """
    if not HAS_OSX_METADATA:
        print(f"Warning: Cannot filter by tag '{tag_name}' - osxmetadata not available")
        return []

    tagged_files = []

    # Walk through the directory
    for root, dirs, files in os.walk(folder_path):
        for folder in dirs:
            dir_path = os.path.join(root, folder)
            try:
                metadata = OSXMetaData(dir_path)
                # Check if the file has the specified tag
                if any(tag.name == tag_name for tag in metadata.tags):
                    tagged_files.append(dir_path)
            except Exception as e:
                print(f"Warning: Could not read metadata for {dir_path}: {e}")
                continue
    return tagged_files

def isRecent(file_path):
    last_modified_time = os.path.getmtime(file_path)
    last_modified_datetime = datetime.fromtimestamp(last_modified_time)
    current_time = datetime.now()
    return (current_time - last_modified_datetime) <= timedelta(hours=24)

def sanitize_string(input_str):
    # Convert to lower case
    lower_str = input_str.lower()
    
    # Replace spaces with "-"
    space_replaced = lower_str.replace(" ", "-")
    
    # Replace any characters not in [a-z,A-Z,0-9,_-] with "-"
    sanitized_str = re.sub(r'[^a-z0-9_-]', '-', space_replaced)
    sanitized_str = re.sub(r'-+', '-', sanitized_str)
    sanitized_str = re.sub(r'-$', '', sanitized_str)
   
    return sanitized_str

# Function to recursively delete empty directories
def delete_empty_dirs(dir_path):
    for root, dirs, _ in os.walk(dir_path, topdown=False):
        for dir in dirs:
            try:
                os.rmdir(os.path.join(root, dir))
            except OSError:
                # Directory is not empty, skip it
                pass

def strip_high_bit(text):
    if not isinstance(text, str):
        text = text.decode('utf-8', errors='replace')     
    # Strip the 8th bit by bitwise AND with 0x7F (0111 1111)
    newText = ''.join(chr(ord(char) & 0x7F) for char in text)
    newText = bytes(newText, 'utf-8').decode('utf-8', 'replace')
    newText = newText.replace("\x00", "\uFFFD") 
    newText = newText.replace("\x1a", "")

    return newText

def find_description_file(directory):
    # List of filenames in priority order
    priority_files = [
        "DISKID",
        "README.TXT",
        "README.DOC",
        "READ.ME",
        "Notes.*"
    ]

    directory_path = Path(directory)

    # Iterate over priority files
    for priority_file in priority_files:
        # Use rglob for both exact and wildcard pattern matches
        for file in directory_path.rglob(priority_file):
            return file

    return None

def extract_filetypes_from_dir(folder_dict, file_list):
         
    debug_print(folder_dict, file_list) 

    for f in file_list:
        path = Path(f)
        filename = path.name
        muster_path = str(path)
        
        debug_print(folder_dict, "Adding muster:" + str(muster_path) + " filename:" + str(filename))
        #create segmented file list
        if path.suffix == '.zip':
            folder_dict["zip_files"].append(muster_path)
        debug_print(folder_dict,"path.suffix: {} path.parent: {}".format(path.suffix, path.parent))
        if path.suffix in IMG_SUFFIXES and "Mustering" in str(path.parent):
            folder_dict["front_jpg_files"].append(muster_path)
        if (path.suffix == '.flux' or path.suffix == '.a2r'):
            folder_dict["flux_files"].append(muster_path)
            folder_dict["hasFluxFile"] = True
        if path.suffix == '.img':
            folder_dict["disk_img_files"].append(muster_path)
            folder_dict["hasDiskImgFile"] = True
        if path.is_dir():
            debug_print(folder_dict,"Adding sub_folder " + muster_path + " to sub_folders")
            folder_dict["sub_folders"].append(muster_path)
            folder_dict["hasFileContents"] = True
        extensions = [".zip", ".flux", ".a2r", ".img"] + IMG_SUFFIXES
        exclude_ext = tuple(extensions) 
        if path.suffix not in extensions:
            folder_dict["other_files"].append(muster_path)
            folder_dict["hasFileContents"] = True
    return

def get_file_details(folder_name, entry_id):
    print(folder_name)
    folder_path = Path(folder_name)
    
    # Skip files and only focus on sub-directories
    exists = check_dir_exists(folder_path)
    if not exists:
        debug_print("Direcotry missing: {}".format(folder_path))
        return None
    
    # Get last modified time for the folder
    last_modified_time = os.path.getmtime(folder_path) 

    # Dictionary to hold folder last modified time and file list
    folder_dict = {
        "id": entry_id,
        "parent_path": folder_path,
        "zip_files": [],
        "front_jpg_files": [],
        "flux_files": [],
        "disk_img_files": [],
        "sub_folders": [],
        "exclude_ext": [],
        "other_files": [],
        "hasFluxFile": False,
        "hasFileContents": False,
        "hasDiskImgFile": False,
        "debug_text": "",
    }

    #check if we need to create a zip file for the contents
    if not zip_contents.has_zip_files(folder_path):
        debug_print(folder_dict, "Creating zip file for {}".format(folder_path))
        zip_contents.create_zip_file(folder_path)
    else:
        debug_print(folder_dict, "{} has Zip file".format(folder_path))
    
    file_list = get_files_from_dir(folder_path) 
    extract_filetypes_from_dir(folder_dict, file_list)
    zip_file_list = zip_contents.get_zip_metadata(folder_path)
    folder_dict["zip_files"] = zip_file_list
    extract_filetypes_from_dir(folder_dict, zip_file_list)

    folder_dict["folder_name"] = folder_path.name
    folder_dict["folder_path"] = str(folder_path)
    folder_dict["identifier"] = sanitize_string(folder_path.name)
    debug_print(folder_dict, folder_dict)

    print(folder_dict)
    return folder_dict

def update_entry_zip_details(folder):
    entry = Entry.objects.get(pk=folder["id"])
    print("\n\n\n\n\nfolder:\n")
    print(folder)

    all_zip_contents = []
    parent = folder['parent_path']
    zip_files = folder.get('zip_files', {})
    #iterating through a list of per disk folders like '/Victor Pulse M160 Knee Toe Graphics'
    for folder_path, folder_data in zip_files.items():
        debug_print(folder, "folder_path:    {}\n".format(folder_path))
        
        #iterating through a set of zip files in the above folder like:
        #/Victor Pulse M160 Knee Toe Graphics/Victor Pulse M160 Knee Toe Graphics.zip
        folder_zip_files = folder_data.get('zip_files', [])
        for zip_file_path, zip_file_data in folder_zip_files.items():
            #creat DB entry for this zip file
            zipfile_db, created = ZipArchive.objects.get_or_create(
                archive = str(zip_file_path),
                entry = entry,
                )
            zipfile_db.save()

            #iterating through the contents of the zip folder
            zip_details = zip_file_data.get('zip_details', [])
            for file_detail in zip_details:
                # Here, you can access individual file details
                # For example, you might want to collect these details in a list
                debug_print(folder, "{}".format(file_detail))
                zipContent, created = ZipContent.objects.get_or_create(
                    file=file_detail["file_path"],
                    zipArchive = zipfile_db,
                    md5sum = file_detail["md5sum"],
                    suffix = file_detail["suffix"],
                    size_bytes = file_detail["size"],
                    )
                zipContent.save()

                #handle a2r meta data
                if file_detail["suffix"] == ".a2r":
                    fluxFile, created = FluxFile.objects.get_or_create(
                            file=file_detail["file_path"],
                            zipContent = zipContent,
                    )
                    fluxFile.save()

                    a2r_data = file_detail['a2r_data']
                    if a2r_data["INFO"] is not None:
                        infoChunk, created = InfoChunk.objects.get_or_create(
                            fluxFile = fluxFile,
                            info_version = a2r_data["INFO"]["info_version"],
                            creator = a2r_data["INFO"]["creator"],
                            drive_type = a2r_data["INFO"]["drive_type"],
                            write_protected = a2r_data["INFO"]["write_protected"],
                            synchronized = a2r_data["INFO"]["synchronized"],
                            hard_sector_count = a2r_data["INFO"]["hard_sector_count"],
                        ) 
                        infoChunk.save()
                    if a2r_data["META"] is not None:
                        metaChunk, created = MetaChunk.objects.get_or_create(
                            fluxFile = fluxFile,
                            title = a2r_data["META"].get("title"),
                            subtitle = a2r_data["META"].get("subtitle"),
                            publisher = a2r_data["META"].get("publisher"),
                            developer = a2r_data["META"].get("developer"),
                            copyright = a2r_data["META"].get("copyright"),
                            version = a2r_data["META"].get("version"),
                            language = MetaChunk.get_language_abbr(a2r_data["META"].get("language")),
                            requires_platform = a2r_data["META"].get("requires_platform"),
                            requires_machine = a2r_data["META"].get("requires_machine"),
                            requires_ram = a2r_data["META"].get("requires_ram"),
                            notes = a2r_data["META"].get("notes"),
                            side = a2r_data["META"].get("side"),
                            side_name = a2r_data["META"].get("side_name"),
                            contributor = a2r_data["META"].get("contributor"),
                            image_date = a2r_data["META"].get("image_date"),
                            )
                        metaChunk.save()
                    
                        debug_print(folder, "fluxfile: {} a2rdata: {}".format(file_detail, a2r_data))
                        publisher = a2r_data["META"].get("publisher")

                if file_detail["suffix"] == ".flux":
                    fluxFile, created = FluxFile.objects.get_or_create(
                            file=file_detail["file_path"],
                            zipContent = zipContent,
                    )
                    fluxFile.save()
                    debug_print(folder, "fluxfile: {}".format(file_detail, fluxFile))
                if "description_file_contents" in file_detail:
                    textFile, created = TextFile.objects.get_or_create(
                        zipContent = zipContent,
                        raw_read = file_detail["description_file_contents"],
                        converted = strip_high_bit(file_detail["description_file_contents"]),
                    )
                    textFile.save()

def update_entry_photo_details(folder):
    entry = Entry.objects.get(pk=folder["id"])
    print("\n\n\n\n\nfolder:\n")
    print(folder)

    all_zip_contents = []
    parent = folder['parent_path']
    jpg_files = folder.get('front_jpg_files', [])
    #insert images

    for name in jpg_files:
        photo, created = PhotoImage.objects.get_or_create(
            image=name,
            entry = entry,
        )
        entry.photos.add(photo)
    entry.save()

def update_entry_collections(folder):
    entry = Entry.objects.get(pk=folder["id"])
    # Handling collections
    collection_names = ['open_source_software']
    for name in collection_names:
        collection, created = ArchCollection.objects.get_or_create(name=name)
        entry.collections.add(collection)
    entry.save()

def update_entry_languages(folder):
    entry = Entry.objects.get(pk=folder["id"])
    # Handling languages
    language_names = ['English']
    if isinstance(language_names, str):
        language_names = [language_names]
    for name in language_names:
        language, created = Language.objects.get_or_create(name=name)
        entry.languages.add(language)
    entry.save()

def update_entry_subjects(folder):
    entry = Entry.objects.get(pk=folder["id"])
    # Handling subjects
    subject_names = ["Victor 9000","ACT Sirius 1"]
    if isinstance(subject_names, str):
        subject_names = subject_names.split(";")
    for name in subject_names:
        subject, created = Subject.objects.get_or_create(name=name)
        entry.subjects.add(subject)  
    entry.save()

def update_entry_details(folder):
    update_entry_photo_details(folder)
    update_entry_collections(folder)
    update_entry_languages(folder)
    update_entry_subjects(folder)
    update_entry_zip_details(folder) 
    return 