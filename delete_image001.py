import os

file_to_delete = "C:\Users\Sanjay Kumar\Evertale Bot\core\image001.py"

try:
    os.remove(file_to_delete)
    print(f"Successfully deleted {file_to_delete}")
except OSError as e:
    print(f"Error deleting file {file_to_delete}: {e}")

