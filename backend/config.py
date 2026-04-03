import os
from pathlib import Path

# Get the backend directory
BASE_DIR = Path(__file__).resolve().parent

# API Keys
GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', '')

# Application settings
DEBUG = True
PORT = 5000

# Network data
NETWORK_FILE = BASE_DIR / 'boston_network.graphml'
CITY = 'Boston, Massachusetts, USA'
NETWORK_TYPE = 'bike' # maybe change this to bike? - did that but could change back to walk

# Algorithm parameters
SA_MAX_ITERATIONS = 500
SA_TEMPERATURE_INITIAL = 100.0
SA_COOLING_RATE = 0.95
SA_NUM_WAYPOINTS = 5

# Route constraints
MIN_DISTANCE_KM = 1.0
MAX_DISTANCE_KM = 50.0
DISTANCE_TOLERANCE = 0.1  # 10% tolerance