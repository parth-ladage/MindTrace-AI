import React, { useRef, useEffect, useState } from 'react';
import { Camera, CameraOff, Brain, Shield, Zap } from 'lucide-react';
import { emotionAPI } from '../utils/api';

const FaceEmotionTracker = ({ onEmotionDetected }) => {
  const videoRef = useRef(null);
  const faceMeshRef = useRef(null);
  const [isActive, setIsActive] = useState(false);
  const [emotion, setEmotion] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const processingRef = useRef(false);

  useEffect(() => {
    if (isActive) {
      initMediaPipe();
    } else {
      stopCamera();
    }
    return () => {
      stopCamera();
    };
  }, [isActive]);

  const initMediaPipe = async () => {
    try {
      setLoading(true);
      if (!window.FaceMesh || !window.Camera) {
        setTimeout(initMediaPipe, 1000);
        return;
      }

      const faceMesh = new window.FaceMesh({
        locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`
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
        video: { width: 640, height: 480 } 
      });

      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        
        const camera = new window.Camera(videoRef.current, {
          onFrame: async () => {
            if (videoRef.current && isActive) {
              await faceMesh.send({image: videoRef.current});
            }
          },
          width: 640,
          height: 480
        });
        camera.start();
      }
      setLoading(false);
      setError(null);
    } catch (err) {
      console.error("Camera error:", err);
      setError("Camera access denied or unavailable.");
      setIsActive(false);
      setLoading(false);
    }
  };

  const stopCamera = () => {
    if (videoRef.current && videoRef.current.srcObject) {
      videoRef.current.srcObject.getTracks().forEach(track => track.stop());
      videoRef.current.srcObject = null;
    }
  };

  const onResults = async (results) => {
    if (!results.multiFaceLandmarks || results.multiFaceLandmarks.length === 0 || processingRef.current) {
      return;
    }

    const landmarks = results.multiFaceLandmarks[0];
    
    // Heuristic analysis (Client Side)
    const faceLeft = landmarks[234], faceRight = landmarks[454];
    const faceWidth = Math.sqrt(Math.pow(faceRight.x - faceLeft.x, 2) + Math.pow(faceRight.y - faceLeft.y, 2)) || 1;
    
    const mouthLeft = landmarks[61], mouthRight = landmarks[291];
    const smileRatio = Math.sqrt(Math.pow(mouthRight.x - mouthLeft.x, 2) + Math.pow(mouthRight.y - mouthLeft.y, 2)) / faceWidth;
    
    const topLip = landmarks[13], bottomLip = landmarks[14];
    const mouthRatio = Math.sqrt(Math.pow(bottomLip.x - topLip.x, 2) + Math.pow(bottomLip.y - topLip.y, 2)) / faceWidth;

    const mouthCenter = landmarks[0];
    const cornersY = (mouthLeft.y + mouthRight.y) / 2;
    const mouthDrop = (cornersY - mouthCenter.y) / faceWidth;

    const leftEyebrow = landmarks[70];
    const leftEye = landmarks[159];
    const eyebrowRatio = Math.sqrt(Math.pow(leftEye.x - leftEyebrow.x, 2) + Math.pow(leftEye.y - leftEyebrow.y, 2)) / faceWidth;

    let detected = 'neutral';
    let intensity = 0.2;

    if (smileRatio > 0.34) { detected = 'joy'; intensity = 0.8; }
    else if (mouthRatio > 0.12) { detected = 'surprise'; intensity = 0.9; }
    else if (mouthDrop > 0.015) { detected = 'sadness'; intensity = 0.6; }
    else if (eyebrowRatio < 0.19) { detected = 'anger'; intensity = 0.7; }
    else if (eyebrowRatio > 0.26) { detected = 'fear'; intensity = 0.7; }

    const emotionData = {
      dominant_emotion: detected.charAt(0).toUpperCase() + detected.slice(1),
      dominant_intensity: intensity,
      timestamp: new Date()
    };

    setEmotion(emotionData);
    onEmotionDetected?.(emotionData);
    
    // Dispatch for global dashboard
    window.dispatchEvent(new CustomEvent('mood-update', { detail: { emotion: detected, intensity } }));

    processingRef.current = true;
    setTimeout(() => { processingRef.current = false; }, 1000);
  };

  return (
    <div className="obsidian-card p-6 relative overflow-hidden">
      <div className="flex items-center justify-between mb-4 relative z-10">
        <div className="flex items-center gap-3">
          <div className={`p-2 rounded-xl ${isActive ? 'bg-indigo-500/10 text-indigo-500' : 'bg-slate-800 text-slate-500'}`}>
            <Camera className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white uppercase tracking-widest">Live Tracking</h3>
            <p className="text-[10px] font-black text-slate-500 tracking-tighter uppercase">Client-Side Private Analysis</p>
          </div>
        </div>
        <button
          onClick={() => setIsActive(!isActive)}
          className={`px-4 py-1.5 rounded-full text-[10px] font-black tracking-widest uppercase transition-all ${
            isActive 
              ? 'bg-red-500/10 border border-red-500/20 text-red-500 hover:bg-red-500/20' 
              : 'bg-indigo-500 text-white shadow-lg shadow-indigo-500/20 hover:scale-105'
          }`}
        >
          {isActive ? 'Disconnect' : 'Connect Vision'}
        </button>
      </div>

      <div className="relative aspect-video rounded-2xl bg-[#0a0a0a] border border-[#1a1a1a] overflow-hidden group">
        {!isActive ? (
          <div className="absolute inset-0 flex flex-col items-center justify-center text-center p-6">
            <CameraOff className="w-10 h-10 text-slate-800 mb-3" />
            <p className="text-xs text-slate-600 font-bold max-w-[180px]">Enable tracking for live private feedback</p>
          </div>
        ) : (
          <>
            <video ref={videoRef} autoPlay muted playsInline className="w-full h-full object-cover grayscale opacity-40 group-hover:grayscale-0 group-hover:opacity-100 transition-all duration-700" />
            <div className="absolute inset-0 border-[20px] border-transparent pointer-events-none">
              <div className="absolute top-0 left-0 w-4 h-4 border-t-2 border-l-2 border-indigo-500/40"></div>
              <div className="absolute top-0 right-0 w-4 h-4 border-t-2 border-r-2 border-indigo-500/40"></div>
              <div className="absolute bottom-0 left-0 w-4 h-4 border-b-2 border-l-2 border-indigo-500/40"></div>
              <div className="absolute bottom-0 right-0 w-4 h-4 border-b-2 border-r-2 border-indigo-500/40"></div>
            </div>
          </>
        )}
      </div>

      {emotion && isActive && (
        <div className="mt-4 p-4 bg-white/5 rounded-2xl border border-white/5 animate-in fade-in slide-in-from-bottom-2">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <Brain className="w-4 h-4 text-indigo-400" />
              <span className="text-[10px] font-black text-gray-400 uppercase tracking-widest">Client State</span>
            </div>
            <span className="text-[10px] font-black text-indigo-500 uppercase tracking-widest">{Math.round(emotion.dominant_intensity * 100)}% Match</span>
          </div>
          <div className="flex items-center justify-between">
            <h4 className="text-xl font-black text-white uppercase">{emotion.dominant_emotion}</h4>
            <div className={`p-1.5 rounded-lg bg-emerald-500/10 text-emerald-500 border border-emerald-500/20`}>
              <Shield className="w-4 h-4" />
            </div>
          </div>
        </div>
      )}

      {error && <p className="mt-3 text-[10px] text-red-400 font-bold text-center italic">{error}</p>}
    </div>
  );
};

export default FaceEmotionTracker;
