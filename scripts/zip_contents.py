#this script will walk a directory and turn all subfolders into zip files and 
#images to upload to the internet archive. any file other than .jpg and .gif 
#goes into a zip file to upload to the internet archive.

import zipfile
import os
import argparse
from osxmetadata import OSXMetaData
import pathlib
from pathlib import Path
from datetime import datetime
import hashlib
import a2r_reader

IMG_SUFFIXES = ['.jpg', '.jpeg', '.gif', '.bmp']

# Function to recursively delete empty directories
def delete_empty_dirs(dir_path):
    for root, dirs, _ in os.walk(dir_path, topdown=False):
        for dir in dirs:
            try:
                os.rmdir(os.path.join(root, dir))
            except OSError:
                # Directory is not empty, skip it
                pass

def find_target_folders(folder_path):
    target_folders = []

    # Walk through the directory
    for root, dirs, files in os.walk(folder_path):
        for folder in dirs:
            dir_path = os.path.join(root, folder)
            metadata = OSXMetaData(dir_path)
            target_folders.append(dir_path)
    return target_folders

def find_zip_files(folder_list):
    folder_dict = {}

    # find Zip files in directory
    for folder in folder_list:
        zip_files = sorted(pathlib.Path(folder).glob('*.zip'))  
        zips = {}
        for zip_file in zip_files:
            zips[zip_file] = { "file_info": zip_file, 
                               "zip_details": {} }    
        folder_dict[folder] = { "zip_files": zips }
    return folder_dict

def has_zip_files(folder):
    folder_dict = find_zip_files([folder])
    for key,value in folder_dict.items():
        if len(value["zip_files"]) > 0:
            return True
    return False

def get_zip_contents(zip_file):
    zip_contents = []
    with zipfile.ZipFile(zip_file, 'r') as zipf:
        for file_info in zipf.infolist():
            #build metadata about each file
            file_meta = {}
            _, file_suffix = os.path.splitext(file_info.filename)

            with zipf.open(file_info) as file:
                # Read the file in chunks and update the MD5 hash
                hash_md5 = hashlib.md5()
                for chunk in iter(lambda: file.read(4096), b""):
                    hash_md5.update(chunk)
                file_meta['md5sum'] = hash_md5.hexdigest()

                if file_suffix == '.a2r':
                    #read meta data out of the A2r
                    file.seek(0, 0)
                    a2r_data = a2r_reader.read_a2r_datastream(file)
                    file_meta["a2r_data"] = a2r_data
             
            file_meta['file_path']= file_info.filename          
            file_meta['suffix'] = file_suffix
            file_meta['size'] = file_info.file_size
            zip_contents.append(file_meta)
    return zip_contents

# zips all the contents of a directory except for .jpg files
# Modified function to fix the bugs and delete empty directories
def create_zip_file(src_dir):
    # Generate ZIP file name based on parent folder name
    parent_folder_name = os.path.basename(src_dir)
    source_dir = Path(src_dir)
    zip_file_name = os.path.join(src_dir, f"{source_dir.name}.zip")
    
    files_to_delete = []
    
    # Initialize ZipFile object
    with zipfile.ZipFile(zip_file_name, 'x', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(src_dir):
            for file in files:
                file_path = Path(root).joinpath(file)

                # Skip .jpg files at the root level and the ZIP file itself
                if (str(root) == str(src_dir) and file_path.suffix in IMG_SUFFIXES) \
                    or file.startswith('.') \
                    or file_path.samefile(zip_file_name):
                    continue
                
                zipf.write(file_path, file_path.relative_to(src_dir))
                
                # Add file to delete list
                files_to_delete.append(file_path)
    
    # Delete the files added to the ZIP
    for file_path in files_to_delete:
        os.remove(file_path)
        
    # Delete empty directories
    delete_empty_dirs(src_dir)
    
    return zip_file_name

def get_zip_details(folder_dict):
    print("folder_dict: {}".format(folder_dict))
    for folder_key, folder_value in folder_dict.items():
        for zip_file,zip_dict in folder_value["zip_files"].items():
            print(zip_file)
            zip_dict["zip_details"] = get_zip_contents(zip_file)
    return folder_dict

def get_zip_metadata(folder_path):
    # Generate the sorted output
    folder_list = find_target_folders(folder_path)
    folder_list.append(folder_path)
    folder_dict = find_zip_files(folder_list)
    print("folder_list: {}".format(folder_list))
    print("folder_dict: {}".format(folder_dict))

    folder_dict = get_zip_details(folder_dict)
    print(f"folder_dict: {folder_dict}")
    return folder_dict

# Main function remains the same
def main():
    parser = argparse.ArgumentParser(description='Ineracts with Zip files for both reading their metadata and creating them for upload.')
    parser.add_argument('src_dir', type=str, help='Looks in the source directory for folders tagged Yellow in Macos')
    args = parser.parse_args()
    parent_path = args.src_dir
    folder_path = Path(parent_path)
    print(f"Reading folder contents from {parent_path} with a Yellow finder tag into disk database.")
    print(f"has_zip_files() returns {has_zip_files(folder_path)}")
    if not has_zip_files(folder_path):
        print("Creating zip file for {}".format(folder_path))
        create_zip_file(folder_path)

    get_zip_metadata(folder_path)
    
    #create_zip_file("/Users/pauldevine/Desktop/Mustering Temp/WordPerfect Developers Toolkit 5.0 v5.0")
    # Sample usage (Note: Replace with actual path for real use)
    current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


if __name__ == "__main__":
    main()
