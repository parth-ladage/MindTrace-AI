import React, { useState, useRef } from 'react';
import { Mic, MicOff, Loader2, Volume2, AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const VoiceEmotionTracker = ({ onResult }) => {
  const { token } = useAuth();
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [recordingTime, setRecordingTime] = useState(0);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const timerRef = useRef(null);

  const API_URL = import.meta.env.VITE_API_URL;

  const startRecording = async () => {
    try {
      setError(null);
      setResult(null);
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach(t => t.stop());
        clearInterval(timerRef.current);
        setRecordingTime(0);

        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        await processAudio(blob);
      };

      mediaRecorder.start();
      setIsRecording(true);
      timerRef.current = setInterval(() => setRecordingTime(prev => prev + 1), 1000);
    } catch (err) {
      setError('Microphone access denied. Please allow microphone permissions.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const processAudio = async (audioBlob) => {
    setIsProcessing(true);
    try {
      const formData = new FormData();
      formData.append('audio', audioBlob, 'recording.webm');

      const response = await fetch(`${API_URL}/api/emotions/detect-audio`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
      });

      if (!response.ok) throw new Error('Audio analysis failed');
      const data = await response.json();
      setResult(data);

      // Dispatch mood-update event for global sync
      if (data.dominant_emotion) {
        window.dispatchEvent(new CustomEvent('mood-update', {
          detail: {
            emotion: data.dominant_emotion,
            intensity: data.dominant_intensity,
            timestamp: new Date()
          }
        }));
      }

      if (onResult) onResult(data);
    } catch (err) {
      setError(err.message || 'Failed to process audio');
    } finally {
      setIsProcessing(false);
    }
  };

  const emotionColorMap = {
    joy: 'text-yellow-400', sadness: 'text-blue-400', anger: 'text-red-400',
    fear: 'text-purple-400', surprise: 'text-pink-400', neutral: 'text-gray-400'
  };

  return (
    <div className="bg-glass border border-borderglass rounded-2xl p-6">
      <div className="flex items-center gap-3 mb-4">
        <Volume2 className="w-5 h-5 text-indigo-400" />
        <h3 className="text-sm font-black tracking-widest uppercase text-foreground">Voice Emotion Sync</h3>
      </div>

      <p className="text-xs text-muted mb-5">
        Record your voice and let AI analyze your emotional state from speech patterns.
      </p>

      {/* Recording Button */}
      <div className="flex flex-col items-center gap-4">
        <button
          onClick={isRecording ? stopRecording : startRecording}
          disabled={isProcessing}
          className={`relative w-20 h-20 rounded-full flex items-center justify-center transition-all duration-300 ${
            isRecording
              ? 'bg-red-500/20 border-2 border-red-500 shadow-[0_0_30px_rgba(239,68,68,0.4)] animate-pulse'
              : isProcessing
                ? 'bg-indigo-500/10 border-2 border-indigo-500/30 cursor-wait'
                : 'bg-indigo-500/20 border-2 border-indigo-500/50 hover:border-indigo-400 hover:shadow-[0_0_20px_rgba(99,102,241,0.3)]'
          }`}
        >
          {isProcessing ? (
            <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
          ) : isRecording ? (
            <MicOff className="w-8 h-8 text-red-400" />
          ) : (
            <Mic className="w-8 h-8 text-indigo-400" />
          )}
        </button>

        <span className="text-[10px] font-bold tracking-widest uppercase text-muted">
          {isProcessing ? 'Analyzing...' : isRecording ? `Recording ${recordingTime}s — Tap to stop` : 'Tap to record'}
        </span>
      </div>

      {/* Error */}
      {error && (
        <div className="mt-4 p-3 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
          <p className="text-xs text-red-300">{error}</p>
        </div>
      )}

      {/* Results */}
      {result && (
        <div className="mt-5 space-y-4">
          {/* Transcription */}
          <div className="p-3 bg-surface rounded-xl border border-borderglass">
            <p className="text-[10px] font-bold tracking-widest uppercase text-muted mb-1">Transcription</p>
            <p className="text-sm text-foreground italic">"{result.transcription}"</p>
          </div>

          {/* Dominant Emotion */}
          <div className="flex items-center justify-between p-3 bg-surface rounded-xl border border-borderglass">
            <div>
              <p className="text-[10px] font-bold tracking-widest uppercase text-muted">Detected Emotion</p>
              <p className={`text-lg font-black capitalize ${emotionColorMap[result.dominant_emotion] || 'text-foreground'}`}>
                {result.dominant_emotion}
              </p>
            </div>
            <div className="text-right">
              <p className="text-[10px] font-bold tracking-widest uppercase text-muted">Intensity</p>
              <p className="text-lg font-black text-foreground">{Math.round(result.dominant_intensity * 100)}%</p>
            </div>
          </div>

          {/* Suggestions */}
          {result.suggestions?.length > 0 && (
            <div className="space-y-2">
              <p className="text-[10px] font-bold tracking-widest uppercase text-muted">Suggestions</p>
              {result.suggestions.map((s, i) => {
                // Parse YouTube links from suggestion text
                const urlMatch = s.match(/\((https:\/\/www\.youtube\.com\/results\?[^)]+)\)/);
                const cleanText = s.replace(/\(https:\/\/www\.youtube\.com\/results\?[^)]+\)/, '').trim();
                return (
                  <div key={i} className="p-2 bg-indigo-500/5 border border-indigo-500/10 rounded-lg">
                    <p className="text-xs text-foreground">{cleanText}</p>
                    {urlMatch && (
                      <a href={urlMatch[1]} target="_blank" rel="noopener noreferrer"
                         className="text-[10px] text-indigo-400 hover:text-indigo-300 underline mt-1 inline-block">
                        ▶ Watch on YouTube
                      </a>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default VoiceEmotionTracker;
