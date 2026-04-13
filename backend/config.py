import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Get the backend directory
BASE_DIR = Path(__file__).resolve().parent

# API key
GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', 'AIzaSyCs5X6o8Bdok0bNES-mr1N2lhm3Sc_6ung')

# App settings
DEBUG = True
PORT = 5000

# Toggle between walk vs bike network
USE_WALK_NETWORK = False

# Get network data
if USE_WALK_NETWORK:
    NETWORK_FILE = BASE_DIR / 'boston_walk_network.graphml'
    NETWORK_TYPE = 'walk'
else:
    NETWORK_FILE = BASE_DIR / 'boston_bike_network.graphml'
    NETWORK_TYPE = 'bike'

# If using city
CITY = 'Boston, Massachusetts, USA'

# If using center and radius
CENTER_POINT = (42.3392, -71.0885) # centered on Cabot
RADIUS = 4000

# Algorithm parameters
SA_MAX_ITERATIONS = 300
SA_INIT_TEMP = 100.0
SA_DECAY = 0.97
SA_NUM_WAYPOINTS = 5

# Route constraints
MIN_DISTANCE_KM = 1.0
MAX_DISTANCE_KM = 50.0
DISTANCE_TOLERANCE = 0.1  # 10% tolerance