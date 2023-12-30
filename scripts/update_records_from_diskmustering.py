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
import create_records_from_diskmustering as mustering

sys.path.insert(0, '/Users/pauldevine/projects/disk_db/victordisk')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "victordisk.settings")
django.setup()
mustering_dir = "/Users/pauldevine/Documents/Victor9k Stuff/Disk Mustering Area/"

from floppies.models import Entry, ArchCollection, Contributor, Creator, FluxFile, InfoChunk, Language, MetaChunk, PhotoImage, Subject, ZipArchive, ZipContent

def debug_print(folder_dict, message):
    print(message)
    folder_dict["debug_text"] += str(message)

def check_dir_exists(directory):
    if not isinstance(directory, str):
        raise ValueError("Both directory and filename must be strings")

    # Construct the full file path
    file_path = Path(directory)

    # Check if the file exists at the specified path
    return os.path.isdir(file_path)

def get_entry_details(id):
    entry = Entry.objects.get(pk=id)
    
    # Dictionary to hold folder last modified time and file list
    folder_dict = {
        "id": id,
        "parent_path": entry.folder,
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
    exists = check_dir_exists(entry.folder)
    if not exists:
        print("Direcotry missing: {} {}".format(entry.id, entry.folder))
        return folder_dict
    if not zip_contents.has_zip_files(entry.folder):
        print("Directory missing zip file: {} {}".format(entry.id, entry.folder))
        return folder_dict

    file_list = mustering.get_files_from_dir(entry.folder) 
    mustering.extract_filetypes_from_dir(folder_dict, file_list)
    zip_file_list = zip_contents.get_zip_metadata(entry.folder)
    folder_dict["zip_files"] = zip_file_list
    mustering.extract_filetypes_from_dir(folder_dict, zip_file_list)
    print(folder_dict)
    return folder_dict

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

def update_entries():
    entries = Entry.objects.all()
    #details = get_entry_details(379)
    for item in entries:
        details = get_entry_details(item.id) 
        update_entry_photo_details(details)
        update_entry_zip_details(details)    

# Main function
def main():
    print("Linking data to file system")
    update_entries()

if __name__ == "__main__":
    main()
