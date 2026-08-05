import React, { useRef, useEffect } from 'react';
import { emotionAPI } from '../utils/api';

const BackgroundEmotionTracker = ({ enabled }) => {
  const videoRef = useRef(null);
  const faceMeshRef = useRef(null);
  const processingRef = useRef(false);
  const emotionBufferRef = useRef([]);
  const BUFFER_SIZE = 5;

  useEffect(() => {
    if (enabled) {
      initMediaPipe();
    } else {
      stopCamera();
    }
    return () => {
      stopCamera();
    };
  }, [enabled]);

  const initMediaPipe = async () => {
    try {
      console.log("Initializing Mood Tracking (MediaPipe)...");
      
      if (!window.isSecureContext) {
        console.error("Camera tracking requires a secure HTTPS connection.");
        return;
      }
      if (!window.FaceMesh || !window.Camera) {
        console.log("MediaPipe scripts not ready, retrying in 1s...");
        setTimeout(initMediaPipe, 1000);
        return;
      }

      // Initialize FaceMesh from the global window object (loaded via script tag)
      const faceMesh = new window.FaceMesh({
        locateFile: (file) => {
          return `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`;
        }
      });

      faceMesh.setOptions({
        maxNumFaces: 1,
        refineLandmarks: true,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5
      });

      faceMesh.onResults(onResults);
      faceMeshRef.current = faceMesh;

      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { width: 320, height: 240, frameRate: 10 } 
      });

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();

        // Start camera utils to feed the video frames to faceMesh
        const camera = new window.Camera(videoRef.current, {
          onFrame: async () => {
            if (videoRef.current) {
              await faceMesh.send({image: videoRef.current});
            }
          },
          width: 320,
          height: 240
        });
        camera.start();
      }
    } catch (err) {
      console.error("Geometric tracking initialization failed:", err);
    }
  };

  const stopCamera = () => {
    if (videoRef.current && videoRef.current.srcObject) {
      console.log("Stopping Geometric Tracker");
      videoRef.current.srcObject.getTracks().forEach(track => track.stop());
      videoRef.current.srcObject = null;
    }
  };

  const tfModelRef = useRef(null);

  // Attempt to load the custom trained TFJS model on mount
  useEffect(() => {
    const loadModel = async () => {
      try {
        const tf = await import('@tensorflow/tfjs');
        const model = await tf.loadLayersModel('/models/emotion_model/model.json');
        console.log("Custom Emotion Neural Network Loaded Successfully!");
        tfModelRef.current = { model, tf };
      } catch (err) {
        console.log("No custom trained model found, defaulting to geometric heuristics. (Did you run train_model.py yet?)");
      }
    };
    loadModel();
  }, []);

  const onResults = async (results) => {
    if (!results.multiFaceLandmarks || results.multiFaceLandmarks.length === 0) return;
    if (processingRef.current) return;
    
    processingRef.current = true;
    
    try {
      let rawEmotion = 'Neutral';
      let rawIntensity = 0.2;
      
      // ==========================================
      // NEURAL NETWORK INFERENCE (If Trained Model Exists)
      // ==========================================
      if (tfModelRef.current && results.image) {
        const { model, tf } = tfModelRef.current;
        const landmarks = results.multiFaceLandmarks[0];
        
        // Find bounding box of the face
        let minX = 1, minY = 1, maxX = 0, maxY = 0;
        landmarks.forEach(p => {
          if (p.x < minX) minX = p.x;
          if (p.y < minY) minY = p.y;
          if (p.x > maxX) maxX = p.x;
          if (p.y > maxY) maxY = p.y;
        });

        // Add 20% padding and make it perfectly square (FER-2013 images are square faces)
        const widthRange = maxX - minX;
        const heightRange = maxY - minY;
        const cx = (minX + maxX) / 2;
        const cy = (minY + maxY) / 2;
        const size = Math.max(widthRange, heightRange) * 1.3; // 30% padding to include hair/chin
        
        minX = Math.max(0, cx - size / 2);
        maxX = Math.min(1, cx + size / 2);
        minY = Math.max(0, cy - size / 2);
        maxY = Math.min(1, cy + size / 2);
        
        // Convert the video frame to a tensor
        const imgTensor = tf.browser.fromPixels(results.image);
        
        // Calculate crop coordinates based on image dimensions
        const [height, width] = imgTensor.shape;
        const y_min = Math.max(0, Math.floor(minY * height));
        const y_max = Math.min(height, Math.floor(maxY * height));
        const x_min = Math.max(0, Math.floor(minX * width));
        const x_max = Math.min(width, Math.floor(maxX * width));
        
        // Crop, resize to 48x48, convert to true luminance grayscale, cast to float, and normalize
        let faceTensor = imgTensor.slice([y_min, x_min, 0], [y_max - y_min, x_max - x_min, 3]);
        faceTensor = tf.image.resizeBilinear(faceTensor, [48, 48]).toFloat();
        
        // Exact formula used by Python PIL during training: L = R * 0.2989 + G * 0.5870 + B * 0.1140
        const rgbWeights = tf.tensor1d([0.2989, 0.5870, 0.1140]);
        faceTensor = faceTensor.mul(rgbWeights).sum(2).expandDims(-1).expandDims(0).div(255.0);
        
        // Predict
        const prediction = await model.predict(faceTensor).data();
        
        // Cleanup tensors
        imgTensor.dispose();
        faceTensor.dispose();
        
        // Keras flow_from_directory sorts folders alphabetically:
        // 0=angry, 1=disgust, 2=fear, 3=happy, 4=neutral, 5=sad, 6=surprise
        const labels = ['Anger', 'Disgust', 'Fear', 'Joy', 'Neutral', 'Sadness', 'Surprise'];
        
        // --- PREDICTION BOOSTER ---
        // FER-2013 CNNs natively struggle with micro-expressions. We manually 
        // boost the confidence of harder-to-detect emotions to make the UI more responsive.
        prediction[0] *= 1.8; // Boost Anger
        prediction[1] *= 2.0; // Boost Disgust
        prediction[2] *= 1.5; // Boost Fear
        
        let maxIdx = 0;
        for(let i=1; i<prediction.length; i++) {
          if (prediction[i] > prediction[maxIdx]) maxIdx = i;
        }
        
        rawEmotion = labels[maxIdx];
        rawIntensity = prediction[maxIdx];
        
      } else {
        // ==========================================
        // GEOMETRIC HEURISTICS (Fallback)
        // ==========================================
        const landmarks = results.multiFaceLandmarks[0];
        const faceLeft = landmarks[234];
        const faceRight = landmarks[454];
        const faceWidth = Math.sqrt(Math.pow(faceRight.x - faceLeft.x, 2) + Math.pow(faceRight.y - faceLeft.y, 2)) || 1;

        const mouthLeft = landmarks[61];
        const mouthRight = landmarks[291];
        const smileRatio = Math.sqrt(Math.pow(mouthRight.x - mouthLeft.x, 2) + Math.pow(mouthRight.y - mouthLeft.y, 2)) / faceWidth;
        
        const topLip = landmarks[13];
        const bottomLip = landmarks[14];
        const mouthRatio = Math.sqrt(Math.pow(bottomLip.x - topLip.x, 2) + Math.pow(bottomLip.y - topLip.y, 2)) / faceWidth;

        const leftEyebrow = landmarks[70];
        const leftEye = landmarks[159];
        const eyebrowRatio = Math.sqrt(Math.pow(leftEye.x - leftEyebrow.x, 2) + Math.pow(leftEye.y - leftEyebrow.y, 2)) / faceWidth;

        const mouthCenter = landmarks[0];
        const mouthDrop = ((mouthLeft.y + mouthRight.y) / 2 - mouthCenter.y) / faceWidth;

        const leftInnerBrow = landmarks[52];
        const rightInnerBrow = landmarks[282];
        const browDistance = Math.sqrt(Math.pow(rightInnerBrow.x - leftInnerBrow.x, 2) + Math.pow(rightInnerBrow.y - leftInnerBrow.y, 2)) / faceWidth;

        const emotions = {
          Joy: (smileRatio - 0.32) * 10,
          Anger: (0.21 - eyebrowRatio) * 12 + (0.12 - browDistance) * 8,
          Surprise: (mouthRatio - 0.12) * 8,
          Sadness: (mouthDrop - 0.01) * 15,
          Fear: (eyebrowRatio - 0.26) * 10 + (mouthRatio * 3)
        };

        Object.keys(emotions).forEach(k => emotions[k] = Math.max(0, Math.min(1.0, emotions[k])));

        if (emotions.Anger > 0.3 && emotions.Joy < 0.15) emotions.Anger *= 1.25;
        if (emotions.Surprise > 0.4 && emotions.Fear > 0.2) emotions.Fear *= 1.15;

        const sorted = Object.entries(emotions).sort((a,b) => b[1] - a[1]);
        if (sorted[0][1] > 0.30) {
          rawEmotion = sorted[0][0];
          rawIntensity = sorted[0][1];
        }
      }

      // Temporal Smoothing (Hysteresis)
      emotionBufferRef.current.push({ emotion: rawEmotion, intensity: rawIntensity });
      if (emotionBufferRef.current.length > BUFFER_SIZE) emotionBufferRef.current.shift();

      const counts = {};
      let dominant = 'Neutral';
      let maxCount = 0;
      let avgIntensity = 0;

      emotionBufferRef.current.forEach(item => {
        counts[item.emotion] = (counts[item.emotion] || 0) + 1;
        if (counts[item.emotion] > maxCount) {
          maxCount = counts[item.emotion];
          dominant = item.emotion;
        }
        avgIntensity += item.intensity;
      });
      avgIntensity /= emotionBufferRef.current.length;

      if (maxCount < BUFFER_SIZE * 0.6) {
        dominant = 'Neutral';
      }

      const syncEvent = new CustomEvent('mood-update', {
        detail: { emotion: dominant, intensity: avgIntensity, timestamp: new Date() }
      });
      window.dispatchEvent(syncEvent);

      await emotionAPI.record({
        emotion: dominant,
        intensity: avgIntensity,
        source: tfModelRef.current ? 'neural_cnn_custom' : 'neural_geometric_v2',
        note: `NEURAL_FUSION: ${maxCount}/${BUFFER_SIZE} stability`,
        timestamp: new Date().toISOString()
      });
      
    } catch (err) {
      console.error("[Neural Tracker] Elevation Sync Error:", err);
    } finally {
      setTimeout(() => { processingRef.current = false; }, 250);
    }
  };
  return (
    <div style={{ position: 'absolute', width: 0, height: 0, overflow: 'hidden', opacity: 0, pointerEvents: 'none' }}>
      <video ref={videoRef} muted playsInline />
    </div>
  );
};

export default BackgroundEmotionTracker;
