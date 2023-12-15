#this script will walk a directory and turn all subfolders into zip files and 
#images to upload to the internet archive. any file other than .jpg and .gif 
#goes into a zip file to upload to the internet archive.

import zipfile
import os
import argparse

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
# Modified function to fix the bugs and delete empty directories
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

# Main function remains the same
def main():
    parser = argparse.ArgumentParser(description='Zip a directory except .jpg files at the root.')
    parser.add_argument('src_dir', type=str, help='The source directory to zip')
    args = parser.parse_args()
    parent_path = args.src_dir
    for folder_name in os.listdir(parent_path):
        folder_path = os.path.join(parent_path, folder_name)
        
        # Skip files and only focus on sub-directories
        if not os.path.isdir(folder_path):
            continue
        zip_file_name = zip_directory_except_jpgs(folder_path)
        print(f"ZIP file created: {zip_file_name}")

if __name__ == "__main__":
    main()
