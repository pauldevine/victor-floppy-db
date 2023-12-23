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

sys.path.insert(0, '/Users/pauldevine/projects/disk_db/victordisk')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "victordisk.settings")
django.setup()
DISK_MUSTERING_DIR = '/Users/pauldevine/Documents/Victor9k Stuff/Disk Mustering Area/'
IMG_SUFFIXES = ['.jpg', '.jpeg', '.png', '.gif', '.bmp']

from floppies.models import Entry, ArchCollection, Contributor, Creator, FluxFile, InfoChunk
from floppies.models import Language, MetaChunk, Subject, PhotoImage, RandoFile, ZipArchive, ZipContent, ImportRun

def debug_print(folder_dict, message):
    print(message)
    folder_dict["debug_text"] += str(message)

def md5(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def get_files_with_tag_in_folder(tag_name, folder_path):
    tagged_files = []

    # Walk through the directory
    for root, dirs, files in os.walk(folder_path):
        for folder in dirs:
            dir_path = os.path.join(root, folder)
            metadata = OSXMetaData(dir_path)

            # Check if the file has the specified tag
            if any(tag.name == tag_name for tag in metadata.tags):
                tagged_files.append(dir_path)
    return tagged_files


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
    # Strip the 8th bit by bitwise AND with 0x7F (0111 1111)
    newText = ''.join(chr(ord(char) & 0x7F) for char in text)
    newText = bytes(newText, 'utf-8').decode('utf-8', 'replace')
    newText = newText.replace("\x00", "\uFFFD") 
    return newText

def insert_into_db(folder_list, sorted_output):
    importRunCreated = False
    for folder in folder_list:
        debug_print(folder, "Inserting into disk_db identifier: {} folder_name{}".format(
            folder['identifier'], folder['folder_name']))
        debug_print(folder, "Folder {}".format(str(folder)))
        if importRunCreated == False:
            importRun = ImportRun(
                text = folder['debug_text'],
                parentPath = folder['parent_path']
            )
            importRun.save()
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
            importRun = importRun,
            description = mydescription
        )

        entry.save()

        #handling zip archives
        for sub_folder, folder_contents in folder["zip_contents"].items():
            zip_files = folder_contents['zip_files']
            for zip_file, zip_dict in zip_files.items():
                zipfile, created = ZipArchive.objects.get_or_create(archive=str(zip_file))
                entry.zipArchives.add(zipfile)
                zipfile.save()
                debug_print(folder, " zipfile: {} zip_dict: {}".format(zipfile, zip_dict))
                #handle zip file contents
                for file in zip_dict["zip_details"]:
                    debug_print(folder, ("   {}".format(file)))
                    zipContent, created = ZipContent.objects.get_or_create(
                        file=file["file_path"],
                        zipArchive = zipfile,
                        md5sum = file["md5sum"],
                        suffix = file["suffix"],
                        size_bytes = file["size"],
                        )
                    zipContent.save()

                    #handle a2r meta data
                    if file["suffix"] == ".a2r":
                        a2r_data = file['a2r_data']
                        infoChunk, created = InfoChunk.objects.get_or_create(
                            info_version = a2r_data["INFO"]["info_version"],
                            creator = a2r_data["INFO"]["creator"],
                            drive_type = a2r_data["INFO"]["drive_type"],
                            write_protected = a2r_data["INFO"]["write_protected"],
                            synchronized = a2r_data["INFO"]["synchronized"],
                            hard_sector_count = a2r_data["INFO"]["hard_sector_count"],
                        ) 
                        infoChunk.save()
                        metaChunk, created = MetaChunk.objects.get_or_create(
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
                        fluxFile, created = FluxFile.objects.get_or_create(
                                file=file["file_path"],
                                zipContent = zipContent,
                                info = infoChunk,
                                meta = metaChunk,
                        )
                        fluxFile.save()
                        entry.fluxFiles.add(fluxFile)
                        debug_print(folder, "fluxfile: {} a2rdata: {}".format(file, a2r_data))
                        publisher = a2r_data["META"].get("publisher")
                        
                        if publisher:
                            contributor, created = Contributor.objects.get_or_create(name=publisher)
                            entry.contributors.add(contributor)
                            
                        developer = a2r_data["META"].get("developer")
                        if developer:
                            creator, created = Creator.objects.get_or_create(name=developer)
                            entry.creators.add(creator)    
                        debug_print(folder, "fluxfile: {} a2rdata: {}".format(file, a2r_data))

                    if file["suffix"] == ".flux":
                        fluxFile, created = FluxFile.objects.get_or_create(
                            file=file["file_path"],
                            zipContent = zipContent,
                            info = None,
                            meta = None,
                        )
                        fluxFile.save()
                        entry.fluxFiles.add(fluxFile)
                        debug_print(folder, "fluxfile: {}".format(file, fluxFile))
           
        #handling images
        if isinstance(folder['front_jpg_files'], str):
            folder['front_jpg_files'] = [folder['front_jpg_files']]
        for name in folder['front_jpg_files']:
            photo, created = PhotoImage.objects.get_or_create(image=name)
            entry.photos.add(photo)

        # Handling collections
        collection_names = ['open_source_software']
        if isinstance(collection_names, str):
            collection_names = [collection_names]
        for name in collection_names:
            collection, created = ArchCollection.objects.get_or_create(name=name)
            entry.collections.add(collection)

        # Handling languages
        language_names = ['English']
        if isinstance(language_names, str):
            language_names = [language_names]
        for name in language_names:
            language, created = Language.objects.get_or_create(name=name)
            entry.languages.add(language)

        # Handling subjects
        subject_names = ["Victor 9000","ACT Sirius 1"]
        if isinstance(subject_names, str):
            subject_names = subject_names.split(";")
        for name in subject_names:
            subject, created = Subject.objects.get_or_create(name=name)
            entry.subjects.add(subject)            
       
        entry.save()
    

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
            file_list + get_files_from_dir(file_path)

    return file_list

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
        if not f.endswith(exclude_ext):
            folder_dict["other_files"].append(muster_path)
            folder_dict["hasFileContents"] = True
        
def build_file_list(folder_list, parent_path):

    tag_name = "Yellow"

    #returns a list of folders that are tagged yellow in the macos finder
    files_with_tag = get_files_with_tag_in_folder(tag_name, parent_path)

    # Iterate through each folder in the parent directory
    for folder_name in files_with_tag:
        # Dictionary to hold folder last modified time and file list
        folder_dict = {
            "parent_path": parent_path,
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

        folder_path = Path(parent_path).joinpath(folder_name)
        mustering_folder = os.path.join(DISK_MUSTERING_DIR, folder_name)
        
        # Skip files and only focus on sub-directories
        if not os.path.isdir(folder_path):
            continue
        
        # Get last modified time for the folder
        last_modified_time = os.path.getmtime(folder_path) 

        #check if we need to create a zip file for the contents
        if not zip_contents.has_zip_files(folder_path):
            debug_print(folder_dict, "Creating zip file for {}".format(folder_path))
            zip_contents.create_zip_file(folder_path)
        else:
            debug_print(folder_dict, "{} has Zip file".format(folder_path))
        
        file_list = get_files_from_dir(folder_path) 
        extract_filetypes_from_dir(folder_dict, file_list)
        folder_dict["zip_contents"] = zip_contents.get_zip_metadata(folder_path)

        zip_file_list = []
        for folder, folder_contents in folder_dict["zip_contents"].items():
            zip_files = folder_contents['zip_files']
            for zip_file, zip_dict in zip_files.items():
                zip_file_list += [d['file_path'] for d in zip_dict["zip_details"] if 'file_path' in d]


        print("zip_file_list:{}".format(zip_file_list))
        extract_filetypes_from_dir(folder_dict, zip_file_list)
        folder_dict["folder_name"] = folder_path.name
        folder_dict["folder_path"] = str(folder_path)
        folder_dict["identifier"] = sanitize_string(folder_path.name)
        debug_print(folder_dict, folder_dict)
        folder_list.append(folder_dict)

        debug_print(folder_dict, "build_file_list() finished '{}', {} folders processed".format(folder_name, len(folder_list)))
        
    debug_print(folder_dict, "Done build_file_list() {} folders processed".format(len(folder_list)))


# Main function remains the same
def main():
    parser = argparse.ArgumentParser(description='Iterates through a local folder and extracts internet archive meta data for django.')
    parser.add_argument('src_dir', type=str, help='Looks in the source directory for folders tagged Yellow in Macos')
    args = parser.parse_args()
    parent_path = args.src_dir
    print("Reading folder contents from " + parent_path + " with a Yellow finder tag into disk database.")

    # Generate the sorted output
    folder_list = []
    build_file_list(folder_list, parent_path)
    print("zip_files: {}".format(folder_list[0]["zip_files"]))
    print("front_jpg_files: {}".format(folder_list[0]["front_jpg_files"]))
    print("flux_files: {}".format(folder_list[0]["flux_files"]))
    print("disk_img_files: {}".format(folder_list[0].get("disk_img_files")))
    insert_into_db(folder_list, parent_path)

    # Sample usage (Note: Replace with actual path for real use)
    current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


if __name__ == "__main__":
    main()
