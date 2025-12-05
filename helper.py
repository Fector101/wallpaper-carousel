import os 
import sys
from datetime import datetime

def makeFolder(my_folder: str):
    """Safely creates a folder if it doesn't exist."""
    # Normalize path for Wine (Windows-on-Linux)
    if is_wine():
        my_folder = my_folder.replace('\\', '/')

   
    if not os.path.exists(my_folder):
        try:
            os.makedirs(my_folder)
        except Exception as e:
            print(f"Error creating folder '{my_folder}': {e}")
    return my_folder


def makeDownloadFolder():
    """Creates (if needed) and returns the Laner download folder path."""
    from kivy.utils import platform

    if platform == 'android':
        from android.storage import primary_external_storage_path  # type: ignore
        folder_path = os.path.join(primary_external_storage_path(), 'Download', 'Laner')
    else:
        folder_path = os.path.join(os.getcwd(), 'Download', 'Laner')

    makeFolder(folder_path)
    return folder_path


class Tee:
    """Redirects writes to both the original stream and a file."""
    def __init__(self, file_path, mode='a'):
        self.file = open(file_path, mode, encoding='utf-8')
        self.stdout = sys.__stdout__  # keep original console output

    def write(self, message):
        # Write to console
        self.stdout.write(message)
        self.stdout.flush()

        # Write to file
        self.file.write(message)
        self.file.flush()

    def flush(self):
        self.stdout.flush()
        self.file.flush()


def start_logging(log_folder_name="logs", file_name="all_output1.txt"):
    # Create folder
    log_folder = os.path.join(makeDownloadFolder(), log_folder_name)
    makeFolder(log_folder)

    # Log file path
    log_file_path = os.path.join(log_folder, file_name)

    # Add a timestamp header for new session
    with open(log_file_path, 'a', encoding='utf-8') as f:
        f.write("\n" + "="*60 + "\n")
        f.write(f"New session started: {datetime.now()}\n")
        f.write("="*60 + "\n")

    # Redirect stdout and stderr
    tee = Tee(log_file_path)
    sys.stdout = tee
    sys.stderr = tee
