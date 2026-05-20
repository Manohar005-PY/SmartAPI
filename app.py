import os
import sys

# Ensure root directory is in the search path for module imports
root_dir = os.path.dirname(os.path.abspath(__file__))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

# Import the Flask application instance from the backend package
from backend.app import app
