#script to generate CSVs for use in uploading via internet archive ia command line
#it reads the files in a hard coded folder and then generates a CSV of the contents
# Importing required modules
import os
import pathlib
from operator import itemgetter
import csv
import re
from datetime import datetime, timedelta
import argparse

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

def list_files_in_dir(parent_path):
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
        
        # List all files in the sub-directory
        file_list = []
        for file_name in os.listdir(folder_path):
            # Ignore hidden files
            if file_name.startswith('.'):
                continue
            
            file_list.append(file_name)
        
        # Sort file list based on criteria
        zip_files = sorted([f for f in file_list if f.endswith('.zip')])
        front_jpg_files = sorted([f for f in file_list if '(Front)' in f and f.endswith('.jpg')])
        other_files = sorted([f for f in file_list if f not in zip_files + front_jpg_files])
        
        # Combine all
        sorted_file_list = zip_files + other_files + front_jpg_files
        
        # Store in dictionary
        folder_dict[folder_path] = {'last_modified': last_modified_time, 'files': sorted_file_list}
        
    # Sort folders by last modified time
    sorted_folders = sorted(folder_dict.items(), key=lambda x: x[1]['last_modified'])
    
    # Generate final sorted output
    sorted_output = []
    headers =["identifier","file","description","subject[0]","subject[1]","subject[2]","title",
              "creator", "date","collection","mediatype","contributor","language"]
    sorted_output.append(headers)
    for folder, folder_info in sorted_folders:
        for file_name in folder_info['files']:
            if file_name.endswith('.zip'):
                lead_row = []
                filename_without_ext = file_name[:file_name.rindex('.')]
                sanitized_name = sanitize_string(filename_without_ext)
                lead_row.append(f"{sanitized_name}")
                lead_row.append(f"{folder}/{file_name}")
                lead_row.extend(["","Victor 9000","ACT Sirius 1","Pulse"])
                lead_row.append(f"{filename_without_ext}")
                lead_row.extend(["Victor Technologies, Inc.","","open_source_software","software",
                                 "Victor Technologies, Inc.","English"])
                sorted_output.append(lead_row)
            else:
                sorted_output.append(["",f"{folder}/{file_name}"])
    
    return sorted_output

# Main function remains the same
def main():
    parser = argparse.ArgumentParser(description='Createa a .csv with a list of files to upload to archive.org')
    parser.add_argument('src_dir', type=str, help='The source directory to create an upload list for')
    args = parser.parse_args()
    parent_path = args.src_dir
    print(parent_path)

    # Define the parent directory (Note: Replace with actual path in real use)
    #parent_path = "/Users/pauldevine/Documents/Victor9k Stuff/Disk Mustering Area"

    # Generate the sorted output
    sorted_output = list_files_in_dir(parent_path)
    for item in sorted_output:
        print(item)

    def generate_csv(sorted_output, csv_file_path):
        with open(csv_file_path, mode ='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(sorted_output)

    # Sample usage (Note: Replace with actual path for real use)
    current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    csv_file_path = f"./sorted_output_{current_datetime}.csv"

    generate_csv(sorted_output, csv_file_path)

if __name__ == "__main__":
    main()

