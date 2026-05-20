import React, { useRef, useEffect } from 'react';
import { emotionAPI } from '../utils/api';

const BackgroundEmotionTracker = ({ enabled }) => {
  const videoRef = useRef(null);
  const faceMeshRef = useRef(null);
  const processingRef = useRef(false);

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

  const emotionBufferRef = useRef([]);
  const BUFFER_SIZE = 15; // Track last 15 frames for stability

  const onResults = async (results) => {
    if (!results.multiFaceLandmarks || results.multiFaceLandmarks.length === 0) return;
    if (processingRef.current) return;

    const landmarks = results.multiFaceLandmarks[0];
    
    // Geometric Calculations
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

    // --- NATURAL NEURAL MAPPING (ELEVATED) ---
    const emotions = {
      Joy: (smileRatio - 0.32) * 10,
      Anger: (0.21 - eyebrowRatio) * 12 + (0.12 - browDistance) * 8,
      Surprise: (mouthRatio - 0.12) * 8,
      Sadness: (mouthDrop - 0.01) * 15, // Reduced multiplier from 70 to 15, increased threshold
      Fear: (eyebrowRatio - 0.26) * 10 + (mouthRatio * 3) // Adjusted threshold and multipliers
    };

    // Apply Natural Dampening & Clamping
    Object.keys(emotions).forEach(k => {
      emotions[k] = Math.max(0, Math.min(1.0, emotions[k]));
    });

    // Detect Compound States (Biological Weighting)
    if (emotions.Anger > 0.3 && emotions.Joy < 0.15) emotions.Anger *= 1.25;
    if (emotions.Surprise > 0.4 && emotions.Fear > 0.2) emotions.Fear *= 1.15;

    let rawEmotion = 'Neutral';
    let rawIntensity = 0.2;
    
    // Find the strongest biological signal — require a minimum of 0.30 to avoid resting-face noise
    const sorted = Object.entries(emotions).sort((a,b) => b[1] - a[1]);
    if (sorted[0][1] > 0.30) {
      rawEmotion = sorted[0][0];
      rawIntensity = sorted[0][1];
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

    // Biological Stability Threshold (60% majority)
    if (maxCount < BUFFER_SIZE * 0.6) {
      dominant = 'Neutral';
    }

    processingRef.current = true;
    try {
      const syncEvent = new CustomEvent('mood-update', {
        detail: { emotion: dominant, intensity: avgIntensity, timestamp: new Date() }
      });
      window.dispatchEvent(syncEvent);

      await emotionAPI.record({
        emotion: dominant,
        intensity: avgIntensity,
        source: 'neural_geometric_v2',
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
