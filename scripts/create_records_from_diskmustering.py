#script to iterate through a folder in the filesystem and create an entry 
#into the disk database for each subfolder. The folder name becomes the title
#any readme or diskid becomes the description
import os
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

sys.path.insert(0, '/Users/pauldevine/projects/disk_db/victordisk')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "victordisk.settings")
django.setup()

from floppies.models import Entry, ArchCollection, Contributor, Creator, FluxFile, Language, Subject, PhotoImage, RandoFile, ZipArchive

# Function to recursively delete empty directories
def delete_empty_dirs(dir_path):
    for root, dirs, _ in os.walk(dir_path, topdown=False):
        for dir in dirs:
            try:
                os.rmdir(os.path.join(root, dir))
            except OSError:
                # Directory is not empty, skip it
                pass


# zips all the contents of a directory except for .jpg files
# Modified function to delete empty directories
def zip_directory_except_jpgs(src_dir):
    # Generate ZIP file name based on parent folder name
    parent_folder_name = os.path.basename(src_dir)
    zip_file_name = os.path.join(src_dir, f"{parent_folder_name}.zip")
    
    files_to_delete = []
    
    # Initialize ZipFile object
    with zipfile.ZipFile(zip_file_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(src_dir):
            for file in files:
                file_path = os.path.join(root, file)
                
                # Skip .jpg files at the root level and the ZIP file itself
                if (root == src_dir and file.endswith('.jpg')) or file_path == zip_file_name:
                    continue
                
                zipf.write(file_path, os.path.relpath(file_path, src_dir))
                
                # Add file to delete list
                files_to_delete.append(file_path)
    
    # Delete the files added to the ZIP
    for file_path in files_to_delete:
        os.remove(file_path)
        
    # Delete empty directories
    delete_empty_dirs(src_dir)
    
    return zip_file_name

def insert_into_db(sorted_output):
    for path, folder in sorted_output:
        print('Inserting into disk_db: ' + folder['identifier'] + ' ' + folder['folder_name'])
        print('Folder' + str(folder))
        entry = Entry(
            identifier = folder['identifier'],
            folder = folder['folder_path'],
            title = folder['folder_name'],
            uploaded = False,
            needsWork = True,
            hasFluxFile = folder['hasFluxFile'],
            hasFileContents = folder['hasFileContents'],
            mediatype = 'SW',
            hasDiskImg = folder['hasDiskImgFile'],
        )
        entry.save()

        #handling zip archives
        if isinstance(folder['zip_filename'], str):
            folder['zip_filename'] = [folder['zip_filename']]
        for name in folder['zip_filename']:
            zipfile, created = ZipArchive.objects.get_or_create(archive=name)
            entry.zipArchives.add(zipfile)

        #handling images
        if isinstance(folder['front_jpg_files'], str):
            folder['front_jpg_files'] = [folder['front_jpg_files']]
        for name in folder['front_jpg_files']:
            photo, created = PhotoImage.objects.get_or_create(image=name)
            entry.photos.add(photo)

        #handling flux files
        if isinstance(folder['flux_files'], str):
            folder['flux_files'] = [folder['flux_files']]
        for name in folder['flux_files']:
            file, created = FluxFile.objects.get_or_create(file=name)
            entry.fluxFiles.add(file)

        if isinstance(folder['other_files'], str):
            folder['other_files'] = [folder['other_files']]
        for name in folder['other_files']:
            print("Adding " + name + " to randoFiles")
            file, created = RandoFile.objects.get_or_create(file=name)
            entry.randoFiles.add(file)

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

def build_file_list(parent_path):
    # Dictionary to hold folder last modified time and file list
    folder_dict = {}
    
    # Iterate through each folder in the parent directory
    for folder_name in os.listdir(parent_path):
        folder_path = os.path.join(parent_path, folder_name)
        
        # Skip files and only focus on sub-directories
        if not os.path.isdir(folder_path):
            continue
        if not isRecent(folder_path):
            continue
        
        # Get last modified time for the folder
        last_modified_time = os.path.getmtime(folder_path)
        
        file_list = get_files_from_dir(folder_path)      
        print(file_list)  
        
        # Sort file list based on criteria
        zip_files = sorted([f for f in file_list if f.endswith('.zip')])
        front_jpg_files = sorted([f for f in file_list if f.endswith('.jpg')])
        flux_files = sorted([f for f in file_list if (f.endswith('.flux') or f.endswith('.a2r'))])
        disk_img_files = sorted([f for f in file_list if f.endswith('.img')])
        sub_folders = sorted([f for f in file_list if os.path.isdir(folder_path)])
        exclude_ext = tuple([".zip", ".jpg", ".flux", ".a2r", ".img" ])
        other_files = sorted([f for f in file_list if not f.endswith(exclude_ext)])

        if len(flux_files) > 0:
            hasFluxFile = True
        else:
            hasFluxFile = False

        if len(sub_folders) > 0:
            hasFileContents = True
        else:
            hasFileContents = False

        if len(disk_img_files) > 0:
            hasDiskImgFile = True
        else:
            hasDiskImgFile = False
        
        #create the zip file for everything but the jpg's
        zip_filename = zip_directory_except_jpgs(folder_path)

        #build identifier
        identifier = sanitize_string(folder_name)

        # Store in dictionary
        folder_dict[folder_path] = {'identifier': identifier,
                                    'folder_name': folder_name,
                                    'folder_path': folder_path,
                                    'last_modified': last_modified_time, 
                                    'zip_filename': zip_filename,
                                    'zip_files': zip_files,
                                    'front_jpg_files': front_jpg_files,
                                    'flux_files': flux_files,
                                    'disk_img_files': disk_img_files,
                                    'sub_folders': sub_folders,
                                    'other_files': other_files,
                                    'hasFluxFile': hasFluxFile,
                                    'hasFileContents': hasFileContents,
                                    'hasDiskImgFile': hasDiskImgFile}
        
    # Sort folders by last modified time
    sorted_folders = sorted(folder_dict.items(), key=lambda x: x[1]['last_modified'])
    print("Found " + str(len(sorted_folders)) + " files.")
    return sorted_folders

# Main function remains the same
def main():
    parser = argparse.ArgumentParser(description='Createa a .csv with a list of files to upload to archive.org')
    parser.add_argument('src_dir', type=str, help='The source directory to create an upload list for')
    args = parser.parse_args()
    parent_path = args.src_dir
    print("Reading folder contents from " + parent_path + " into disk database.")

    # Generate the sorted output
    sorted_output = build_file_list(parent_path)
    insert_into_db(sorted_output)

    # Sample usage (Note: Replace with actual path for real use)
    current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


if __name__ == "__main__":
    main()
