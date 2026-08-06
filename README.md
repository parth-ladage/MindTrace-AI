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

```bash
cd /home/parth-ladage/projects/MindTrace-AI/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a local environment file:

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

Run the backend:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open the API docs at:

```text
http://localhost:8000/docs
```

## 2) Frontend setup

```bash
cd /home/parth-ladage/projects/MindTrace-AI/frontend
npm install
npm run dev
```

Open the app at:

```text
http://localhost:5173
```

## 3) ML model training

```bash
cd /home/parth-ladage/projects/MindTrace-AI/ml_model
python3 -m venv .venv
source .venv/bin/activate
pip install tensorflow tensorflowjs opencv-python numpy pandas matplotlib
python3 train_model.py
```

The training script will generate model artifacts that can be used by the frontend if you copy them into the public models directory.

## 4) MLflow setup

The backend already contains MLflow configuration in the app core package. To run and inspect MLflow locally:

```bash
cd /home/parth-ladage/projects/MindTrace-AI/backend
source .venv/bin/activate
mlflow ui --backend-store-uri sqlite:///mlflow.db --default-artifact-root ./mlruns
```

Then open:

```text
http://localhost:5000
```

To verify the MLflow integration:

```bash
cd /home/parth-ladage/projects/MindTrace-AI/backend
source .venv/bin/activate
python3 tests/test_mlflow_smoke.py
```

## 5) Useful development commands

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

## Documentation

- [USER_GUIDE.md](USER_GUIDE.md) for API usage and examples
- [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) for deeper architecture notes
- [backend/README.md](backend/README.md) for backend-specific details
- [ml_model/README.md](ml_model/README.md) for training instructions

## Notes

- The backend is designed to work with or without optional AI dependencies, so some features may gracefully degrade if ML packages are missing.
- The frontend is a Vite React app and uses the components folder heavily for the dashboard experience.
- The repository also contains evaluation CSVs and model comparison outputs used for experimentation and reporting.
