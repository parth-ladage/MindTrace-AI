import os
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Dense, Dropout, Flatten, BatchNormalization
from tensorflow.keras.preprocessing.image import ImageDataGenerator
import subprocess

# ==========================================
# CONFIGURATION
# ==========================================
DATASET_DIR = "fer2013" # The folder containing 'train' and 'test' subfolders
IMG_SIZE = 48
BATCH_SIZE = 64
EPOCHS = 35

# Emotion mapping in FER-2013 dataset
# 0=Angry, 1=Disgust, 2=Fear, 3=Happy, 4=Sad, 5=Surprise, 6=Neutral
NUM_CLASSES = 7

def build_model():
    """Builds a lightweight CNN suitable for running in the browser."""
    model = Sequential([
        # Block 1
        Conv2D(32, kernel_size=(3, 3), activation='relu', input_shape=(IMG_SIZE, IMG_SIZE, 1)),
        BatchNormalization(),
        Conv2D(32, kernel_size=(3, 3), activation='relu'),
        BatchNormalization(),
        MaxPooling2D(pool_size=(2, 2)),
        Dropout(0.25),

        # Block 2
        Conv2D(64, kernel_size=(3, 3), activation='relu'),
        BatchNormalization(),
        Conv2D(64, kernel_size=(3, 3), activation='relu'),
        BatchNormalization(),
        MaxPooling2D(pool_size=(2, 2)),
        Dropout(0.25),

        # Block 3
        Conv2D(128, kernel_size=(3, 3), activation='relu'),
        BatchNormalization(),
        MaxPooling2D(pool_size=(2, 2)),
        Dropout(0.25),

        # Flatten & Dense Layers
        Flatten(),
        Dense(256, activation='relu'),
        BatchNormalization(),
        Dropout(0.5),
        Dense(NUM_CLASSES, activation='softmax')
    ])
    
    model.compile(optimizer='adam', 
                  loss='categorical_crossentropy', 
                  metrics=['accuracy'])
    return model

def main():
    if not os.path.exists(os.path.join(DATASET_DIR, "train")):
        print(f"ERROR: Could not find the training data at {os.path.join(DATASET_DIR, 'train')}.")
        print("Please download the FER-2013 dataset from Kaggle, extract it, and place it in the 'ml_model/fer2013' folder.")
        return

    # Data Augmentation prevents overfitting
    train_datagen = ImageDataGenerator(
        rescale=1./255,
        rotation_range=10,
        width_shift_range=0.1,
        height_shift_range=0.1,
        horizontal_flip=True,
        fill_mode='nearest'
    )

    test_datagen = ImageDataGenerator(rescale=1./255)

    train_generator = train_datagen.flow_from_directory(
        os.path.join(DATASET_DIR, 'train'),
        target_size=(IMG_SIZE, IMG_SIZE),
        color_mode="grayscale",
        batch_size=BATCH_SIZE,
        class_mode='categorical'
    )

    validation_generator = test_datagen.flow_from_directory(
        os.path.join(DATASET_DIR, 'test'),
        target_size=(IMG_SIZE, IMG_SIZE),
        color_mode="grayscale",
        batch_size=BATCH_SIZE,
        class_mode='categorical'
    )

    model = build_model()
    model.summary()

    print("\nStarting Training...")
    history = model.fit(
        train_generator,
        epochs=EPOCHS,
        validation_data=validation_generator
    )

    # Save Python model
    model_path = "emotion_model.h5"
    model.save(model_path)
    print(f"\nModel saved successfully as {model_path}")

    print("\nConverting model to TensorFlow.js format...")
    tfjs_dir = "tfjs_model"
    if not os.path.exists(tfjs_dir):
        os.makedirs(tfjs_dir)
        
    try:
        # Fix for Python 3.12 and newer Numpy versions that broke tensorflowjs
        import numpy as np
        if not hasattr(np, 'object'):
            np.object = object
            np.bool = bool
            np.int = int
            np.typeDict = np.sctypeDict

        # Fix for TensorFlow 2.16+ which removed estimator, breaking tensorflow_hub
        import tensorflow as tf
        if not hasattr(tf.compat.v1, 'estimator'):
            tf.compat.v1.estimator = type('estimator', (), {'Exporter': object})

        import tensorflowjs as tfjs
        tfjs.converters.save_keras_model(model, tfjs_dir)
        print(f"\nSUCCESS! Your web-ready model is in the '{tfjs_dir}' folder.")
        print("Copy the contents of this folder into 'frontend/public/models/emotion_model/' to use it in MindTrace AI+!")
    except Exception as e:
        print("\nERROR during conversion.")
        print(e)

if __name__ == "__main__":
    main()
