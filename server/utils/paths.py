
import os
import sys

def get_app_data_dir():
    """Returns the writable directory for persistent data (configs, logs, db)."""
    if getattr(sys, 'frozen', False):
        # We are running as an EXE
        # Professional Windows approach: %APPDATA%/NetworkToolsV3
        app_data = os.getenv('APPDATA')
        if app_data:
            path = os.path.join(app_data, "NetworkToolsV3")
        else:
            # Fallback to local folder if APPDATA is missing (rare)
            path = os.path.join(os.path.dirname(sys.executable), "data")
    else:
        # Running in development mode
        path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    return os.path.abspath(path)

def get_file_path(filename):
    """Returns the absolute path for a data file in the app data directory."""
    return os.path.join(get_app_data_dir(), filename)

def get_bundle_resource_path(relative_path):
    """Returns absolute path for read-only resources (frontend, models, icons)."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    # Default path for development
    return os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), relative_path))
