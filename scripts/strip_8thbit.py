#this script will take a text file created by wordstar or some earlier word
#processor and strip out the 8th bit, which was used for formating information
#the text values are striaght 7-bit ascii but modern OSs can't understand
#the 8th bit and turn the text into garbage.
import sys

def strip_high_bit(text):
    # Strip the 8th bit by bitwise AND with 0x7F (0111 1111)
    return ''.join(chr(ord(char) & 0x7F) for char in text)

def convert_file(filename):
    # Read the original file
    with open(filename, 'r', encoding='latin1') as f:
        original_text = f.read()
    
    # Perform the conversion
    cleaned_text = strip_high_bit(original_text)
    
    # Write to a new file
    new_filename = filename.split('.')[0] + '_converted.txt'
    with open(new_filename, 'w', encoding='utf-8') as f:
        f.write(cleaned_text)

    print(f"File converted and saved as {new_filename}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <filename>")
        sys.exit(1)
    
    filename = sys.argv[1]
    convert_file(filename)
