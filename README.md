# PATH - AI Route Generator

Generate optimal running and cycling routes using local search algorithms.

## Quick Start

### 1. Install Dependencies
```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Backend
```bash
cd backend
python app.py
```

First run will download Boston network, which may take a little bit because there are over 50,000 nodes!

### 3. Run Frontend

Open new terminal:
```bash
cd frontend
python -m http.server 8000
```

Open http://localhost:8000

## How to Use

1. Click on map to set starting point
2. Enter desired distance (in km)
3. Select elevation preference
4. Click "Generate Route"
5. Route appears on map!

## Project Structure
```
path/
├── backend/          # Python Flask API
│   ├── algorithms/   # Simulated annealing
│   ├── services/     # Network & stats
│   └── app.py       # Main API
├── frontend/        # Web interface
└── README.md
```