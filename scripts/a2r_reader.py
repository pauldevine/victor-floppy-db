import struct

# Constants for chunk IDs (assuming these are defined elsewhere in your C code)
INFO_CHUNK_ID = b'INFO'  # Replace with the actual value
RWCP_CHUNK_ID = b'RWCP'  # Replace with the actual value
SLVD_CHUNK_ID = b'SLVD'  # Replace with the actual value
META_CHUNK_ID = b'META'  # Replace with the actual value

DEBUG = False

def parse_a2r_info_chunk(data):
    # Parse the INFO chunk based on the provided specification
    info_version = struct.unpack_from("<B", data, 0)[0]  # 1 byte at offset 0
    creator = data[1:33].decode('utf-8').rstrip(' ')     # 32 bytes at offset 1
    drive_type = struct.unpack_from("<B", data, 33)[0]   # 1 byte at offset 33
    write_protected = struct.unpack_from("<B", data, 34)[0]  # 1 byte at offset 34
    synchronized = struct.unpack_from("<B", data, 35)[0] # 1 byte at offset 35
    hard_sector_count = struct.unpack_from("<B", data, 36)[0] # 1 byte at offset 36

    return {
        "info_version": info_version,
        "creator": creator,
        "drive_type": drive_type,
        "write_protected": write_protected,
        "synchronized": synchronized,
        "hard_sector_count": hard_sector_count
    }

def parse_a2r_meta_chunk(data):
    # Decode the binary data to string
    meta_str = data.decode('UTF-8')
    
    # Split the string into lines
    lines = meta_str.strip().split('\n')
        
    # Dictionary to hold the parsed metadata
    meta_data = {}

    # Iterate over each line and extract key-value pairs
    for line in lines:
        # Split the line by tab to separate key and value
        parts = line.split('\t')
        
        # Check if line has at least two parts (key and value)
        if len(parts) >= 2:
            key = parts[0].strip()
            value = parts[1].strip()
            meta_data[key] = value

    return meta_data

def read_a2r_file(filename):
    a2r_data = {
        "INFO": None,
        "META": None
    }
    with open(filename, 'rb') as data_stream:
        return read_a2r_datastream(data_stream)

def read_a2r_datastream(data_stream):
    a2r_data = {
        "INFO": None,
        "META": None
    }
    # Skip the initial 8-byte header
    file_header = data_stream.read(8)

    while True:
        # Read the next chunk header
        header = data_stream.read(8)
        if len(header) < 8:
            break  # End of file or incomplete chunk

        chunk_id, chunk_size = struct.unpack("<4sI", header)
        if DEBUG:
            print("Chunk ID: {}, Chunk Size: {}".format(chunk_id, chunk_size))

        # Ensure to read or skip the entire chunk to align for the next chunk
        if chunk_id == b'INFO':
            # Read the INFO chunk data and parse it
            info_data = data_stream.read(chunk_size)
            a2r_data["INFO"] = parse_a2r_info_chunk(info_data)
        elif chunk_id == b'RWCP':
            # Process RWCP chunk
            rwcp_data = data_stream.read(chunk_size)
            # ... (Process rwcp_data)
        elif chunk_id == b'META':
            # Read the META chunk data and parse it
            meta_data = data_stream.read(chunk_size)
            a2r_data["META"] = parse_a2r_meta_chunk(meta_data)
        else:
            # Skip unknown chunks
            data_stream.seek(chunk_size, 1)

        # Debugging: Show the file position after processing each chunk
        if DEBUG:
            print("File position after chunk: {}".format(data_stream.tell()))
    return a2r_data

if __name__ == "__main__":
    DEBUG = True
    # Example usage
    filename = "/Users/pauldevine/Desktop/13-Nov Disk Muster copy/WordPerfect Victor 1984 - WordPerfect Victor 1984.a2r"
    a2r_metadata = read_a2r_file(filename)
    print(a2r_metadata)
