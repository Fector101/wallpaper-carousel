import os, platform
import sys
from datetime import datetime
from jnius import autoclass, cast

def is_wine():
	"""
	Detect if the application is running under Wine.
	"""
	# Check environment variables set by Wine
	if "WINELOADER" in os.environ:
		return True

	# Check platform.system for specific hints
	if platform.system().lower() == "windows":
	# If running in "Windows" mode but in a Linux environment, it's likely Wine
		return "XDG_SESSION_TYPE" in os.environ or "HOME" in os.environ

	return False
    
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



class Service:
    def __init__(self,name,args_str="",extra=True):
        from android import mActivity
        self.mActivity = mActivity
        self.args_str=args_str
        self.name=name
        self.extra=extra
        self.start_service_if_not_running()
    def get_service_name(self):
        context = self.mActivity.getApplicationContext()
        return str(context.getPackageName()) + '.Service' + self.name

    def service_is_running(self):
        service_name = self.get_service_name()
        context = self.mActivity.getApplicationContext()
        thing=self.mActivity.getSystemService(context.ACTIVITY_SERVICE)
        
        manager = cast('android.app.ActivityManager',thing)
        for service in manager.getRunningServices(100):
        	found_service=service.service.getClassName()
        	print("found_service: ",found_service)
        	if found_service== service_name:
        		return True
        return False
            #
            
        

    def start_service_if_not_running(self):
    	state=self.service_is_running()
    	print(state,"||",self.name,"||", self.get_service_name())
    	if state:
    		return
    	service = autoclass(self.get_service_name())
    	title=self.name +' Service'
    	msg='Started'
    	arg=str(self.args_str)
    	icon='round_music_note_white_24'
    	if self.extra:
    		service.start(self.mActivity, icon, title, msg, arg)
    	else:
    		service.start(self.mActivity, arg)
    	
