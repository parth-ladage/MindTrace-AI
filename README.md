# MINDTRACE AI+ — Emotional Intelligence Platform

MINDTRACE AI+ is a full-stack emotional wellness platform with a FastAPI backend, a React/Vite frontend, and a custom machine learning model for emotion analysis.

## Current repository structure

```text
.
├── backend/
│   ├── app/
│   │   ├── ai/
│   │   ├── api/
│   │   ├── core/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── utils/
│   │   └── websocket/
│   ├── main.py
│   ├── requirements.txt
│   ├── locustfile.py
│   ├── mindtrace_emotional_support_dataset.csv
│   ├── mlruns/
│   └── tests/
├── frontend/
│   ├── public/
│   ├── simple_client/
│   ├── src/
│   │   ├── components/
│   │   ├── context/
│   │   ├── hooks/
│   │   ├── utils/
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
├── ml_model/
│   ├── train_model.py
│   ├── emotion_model.h5
│   ├── fer2013/
│   ├── colab_training.ipynb
│   └── README.md
├── render.yaml
├── requirements.txt
├── USER_GUIDE.md
├── PROJECT_STRUCTURE.md
└── README.md
```

## What is included

- FastAPI backend with authentication, journal tracking, interventions, analytics, and WebSockets
- React + Vite frontend with dashboard-style UI components
- Custom FER model training pipeline under ml_model/
- MLflow integration for experiment tracking in the backend
- Evaluation and model comparison artifacts in the repository root

## Prerequisites

- Python 3.10+ or 3.11+
- Node.js 18+ and npm
- MongoDB (optional for local development, but the app is configured to use it)
- Redis (optional for local development)

## 1) Backend setup

### Linux / macOS

```bash
cd /home/parth-ladage/projects/MindTrace-AI/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Windows PowerShell

```powershell
cd C:\path\to\MindTrace-AI\backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create a local environment file:

### Linux / macOS

```bash
cat > .env <<'EOF'
SECRET_KEY=change-this-secret
MONGODB_URL=mongodb://localhost:27017/mindtrace
MONGODB_DB=mindtrace_db
REDIS_URL=redis://localhost:6379/0
MLFLOW_ENABLED=True
MLFLOW_TRACKING_URI=./mlruns
MLFLOW_EXPERIMENT_PREFIX=MindTrace
EOF
```

### Windows PowerShell

```powershell
@"
SECRET_KEY=change-this-secret
MONGODB_URL=mongodb://localhost:27017/mindtrace
MONGODB_DB=mindtrace_db
REDIS_URL=redis://localhost:6379/0
MLFLOW_ENABLED=True
MLFLOW_TRACKING_URI=./mlruns
MLFLOW_EXPERIMENT_PREFIX=MindTrace
"@ | Set-Content .env
```

Run the backend:

### Linux / macOS

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Windows PowerShell

```powershell
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open the API docs at:

```text
http://localhost:8000/docs
```

## 2) Frontend setup

### Linux / macOS

```bash
cd /home/parth-ladage/projects/MindTrace-AI/frontend
npm install
npm run dev
```

### Windows PowerShell

```powershell
cd C:\path\to\MindTrace-AI\frontend
npm install
npm run dev
```

Open the app at:

```text
http://localhost:5173
```

## 3) ML model training

### Linux / macOS

```bash
cd /home/parth-ladage/projects/MindTrace-AI/ml_model
python3 -m venv .venv
source .venv/bin/activate
pip install tensorflow tensorflowjs opencv-python numpy pandas matplotlib
python3 train_model.py
```

### Windows PowerShell

```powershell
cd C:\path\to\MindTrace-AI\ml_model
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install tensorflow tensorflowjs opencv-python numpy pandas matplotlib
python train_model.py
```

The training script will generate model artifacts that can be used by the frontend if you copy them into the public models directory.

## 4) MLflow setup

The backend already contains MLflow configuration in the app core package. Follow these steps to configure and run it locally.

### 4.1 Install MLflow

#### Linux / macOS

```bash
cd /home/parth-ladage/projects/MindTrace-AI/backend
source .venv/bin/activate
pip install mlflow>=2.12.0
```

#### Windows PowerShell

```powershell
cd C:\path\to\MindTrace-AI\backend
.\.venv\Scripts\Activate.ps1
pip install mlflow>=2.12.0
```

### 4.2 Configure environment variables

Make sure your backend environment includes:

#### Linux / macOS

```bash
export MLFLOW_ENABLED=True
export MLFLOW_TRACKING_URI=./mlruns
export MLFLOW_EXPERIMENT_PREFIX=MindTrace
```

#### Windows PowerShell

```powershell
$env:MLFLOW_ENABLED="True"
$env:MLFLOW_TRACKING_URI="./mlruns"
$env:MLFLOW_EXPERIMENT_PREFIX="MindTrace"
```

You can also add them to your backend `.env` file as shown in the backend setup section.

### 4.3 Start the MLflow tracking UI

Run the following command in a separate terminal:

#### Linux / macOS

```bash
cd /home/parth-ladage/projects/MindTrace-AI/backend
source .venv/bin/activate
mlflow ui --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlruns
```

#### Windows PowerShell

```powershell
cd C:\path\to\MindTrace-AI\backend
.\.venv\Scripts\Activate.ps1
mlflow ui --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlruns
```

Then open:

```text
http://localhost:5000
```

### 4.4 Run the backend with MLflow enabled

In another terminal, start the FastAPI backend:

#### Linux / macOS

```bash
cd /home/parth-ladage/projects/MindTrace-AI/backend
source .venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Windows PowerShell

```powershell
cd C:\path\to\MindTrace-AI\backend
.\.venv\Scripts\Activate.ps1
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4.5 Verify MLflow integration

Run the smoke test:

#### Linux / macOS

```bash
cd /home/parth-ladage/projects/MindTrace-AI/backend
source .venv/bin/activate
python3 tests/test_mlflow_smoke.py
```

#### Windows PowerShell

```powershell
cd C:\path\to\MindTrace-AI\backend
.\.venv\Scripts\Activate.ps1
python tests/test_mlflow_smoke.py
```

This should create or update runs under the backend mlruns directory and allow you to view them in the MLflow UI.

## 5) Useful development commands

### Linux / macOS

Backend tests:

```bash
cd /home/parth-ladage/projects/MindTrace-AI/backend
source .venv/bin/activate
pytest tests/
```

Load testing:

```bash
cd /home/parth-ladage/projects/MindTrace-AI/backend
source .venv/bin/activate
python3 -m locust -f locustfile.py --host http://localhost:8000
```

### Windows PowerShell

Backend tests:

```powershell
cd C:\path\to\MindTrace-AI\backend
.\.venv\Scripts\Activate.ps1
pytest tests/
```

Load testing:

```powershell
cd C:\path\to\MindTrace-AI\backend
.\.venv\Scripts\Activate.ps1
python -m locust -f locustfile.py --host http://localhost:8000
```

## Documentation

- [USER_GUIDE.md](USER_GUIDE.md) for API usage and examples
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for deeper architecture notes
- [backend/README.md](backend/README.md) for backend-specific details
- [ml_model/README.md](ml_model/README.md) for training instructions

## Notes

- The backend is designed to work with or without optional AI dependencies, so some features may gracefully degrade if ML packages are missing.
- The frontend is a Vite React app and uses the components folder heavily for the dashboard experience.
- The repository also contains evaluation CSVs and model comparison outputs used for experimentation and reporting.
