# MindTrace Custom Emotion Model Training

This directory contains the scripts needed to train your own custom Facial Expression Recognition (FER) neural network from scratch.

## Prerequisites

You need Python installed on your machine. We highly recommend using a Virtual Environment.

1. Open your terminal in this `ml_model` directory.
2. Create and activate a virtual environment:
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate
   
   # Mac/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install the required Machine Learning libraries:
   ```bash
   pip install tensorflow tensorflowjs opencv-python numpy pandas matplotlib
   ```

## Step 1: Download the Dataset

We are using the FER-2013 dataset.
1. Go to [Kaggle FER-2013 Dataset](https://www.kaggle.com/datasets/msambare/fer2013).
2. Download and extract the archive.
3. Rename the extracted folder to `fer2013` and place it directly inside this `ml_model` directory.
   
Your folder structure should look like this:
```
ml_model/
  ├── fer2013/
  │    ├── train/
  │    │    ├── angry/
  │    │    ├── happy/
  │    │    └── ...
  │    └── test/
  ├── train_model.py
  └── README.md
```

## Step 2: Train the Model

Simply run the training script! Depending on your CPU/GPU, this might take 30 minutes to a few hours.

```bash
python train_model.py
```

## Step 3: Deploy to the Frontend

Once the script finishes successfully, it will create a folder called `tfjs_model`.
This folder contains `model.json` and several `.bin` files.

1. Copy the entire contents of the `tfjs_model` folder.
2. Paste them into your frontend directory at:
   `MindTrace-AI-/frontend/public/models/emotion_model/`
3. The React app is already coded to detect and load this model if it exists!
