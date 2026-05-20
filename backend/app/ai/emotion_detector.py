import asyncio
import httpx
import logging
from typing import Dict, List, Optional
from datetime import datetime
from app.services.groq_service import groq_service
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmotionDetectionEngine:
    def __init__(self):
        self.api_token = settings.HUGGINGFACE_TOKEN
        self.emotion_url = f"https://api-inference.huggingface.co/models/{settings.EMOTION_MODEL}"
        self.sentiment_url = f"https://api-inference.huggingface.co/models/{settings.SENTIMENT_MODEL}"
        self.face_emotion_url = "https://api-inference.huggingface.co/models/dima806/facial_emotions_image_detection"
        self._initialized = False
        self._cache = {} 
    
    async def initialize(self):
        self._initialized = True
        logger.info("✓ Emotion Detection Engine initialized")

    async def _call_hf_api(self, url: str, text: str) -> Optional[List[Dict]]:
        if not self.api_token:
            return None
        
        headers = {"Authorization": f"Bearer {self.api_token}"}
        try:
            async with httpx.AsyncClient() as client:
                # Fixed URL structure if needed, but keeping it as is for now and prioritizing Groq
                response = await client.post(url, headers=headers, json={"inputs": text}, timeout=10.0)
            
            if response.status_code == 200:
                data = response.json()
                return data[0] if isinstance(data, list) and isinstance(data[0], list) else data
            return None
        except Exception as e:
            logger.error(f"HF API Error: {e}")
            return None

    async def detect_emotions_groq(self, text: str) -> Dict[str, float]:
        """Detect emotions using Groq (Llama 3.3 70B) for high accuracy with anti-bias safeguards"""
        if not groq_service.client:
            return {}
        
        try:
            system_prompt = (
                "You are an objective, clinical-grade sentiment classifier. "
                "You MUST NOT over-diagnose sadness, anger, or fear. "
                "If the text is casual, factual, or lacks strong emotional language, "
                "assign 'neutral' a high score (0.6+). "
                "Only assign negative emotions high scores when the language clearly and explicitly expresses them. "
                "Be balanced and precise."
            )
            prompt = (
                f"Classify the emotions in this text: \"{text}\". "
                "Return ONLY a valid JSON object with these exact keys: joy, sadness, anger, fear, surprise, neutral. "
                "Values must be floats from 0.0 to 1.0 and should sum to approximately 1.0. "
                "No other text or explanation."
            )
            chat_completion = await groq_service.client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                model="llama-3.3-70b-versatile",
                max_tokens=100,
                temperature=0.0,
                response_format={"type": "json_object"}
            )
            import json
            emotions = json.loads(chat_completion.choices[0].message.content)
            
            # Normalize: ensure all expected keys exist
            for key in ["joy", "sadness", "anger", "fear", "surprise", "neutral"]:
                if key not in emotions:
                    emotions[key] = 0.0
            
            return emotions
        except Exception as e:
            logger.error(f"Groq Emotion Detection Error: {e}")
            return {}

    async def analyze_text_comprehensive(self, text: str) -> Dict:
        """Comprehensive analysis using Groq for superior insights with anti-bias safeguards"""
        text_clean = text.strip().lower()
        if text_clean in self._cache:
            result = self._cache[text_clean].copy()
            result["timestamp"] = datetime.now().isoformat()
            result["cached"] = True
            return result

        # Prioritize Groq for detection
        emotions = await self.detect_emotions_groq(text)
        
        # Fallback to HF then keywords if Groq fails
        if not emotions:
            hf_results = await self._call_hf_api(self.emotion_url, text)
            if hf_results:
                emotions = {r['label'].lower(): r['score'] for r in hf_results}
            else:
                emotions = self._fallback_emotions(text)
        
        dominant_emotion = max(emotions, key=emotions.get) if emotions else "neutral"
        dominant_intensity = emotions.get(dominant_emotion, 0)
        
        # ANTI-BIAS SAFEGUARD: If the highest emotion intensity is very low,
        # override to neutral to prevent false-positive negative emotions.
        if dominant_intensity < 0.3 and dominant_emotion != "neutral":
            dominant_emotion = "neutral"
            dominant_intensity = emotions.get("neutral", 0.5)
        
        # Improved positivity calculation with balanced weighting
        positive_score = emotions.get("joy", 0) + emotions.get("surprise", 0) * 0.5 + emotions.get("neutral", 0) * 0.4
        negative_score = emotions.get("sadness", 0) + emotions.get("anger", 0) + emotions.get("fear", 0) * 0.8
        total = positive_score + negative_score + 0.001  # avoid division by zero
        positivity = max(0.0, min(1.0, positive_score / total))

        # Generate personalized suggestion via Groq
        suggestions = await groq_service.get_personalized_suggestions(dominant_emotion, dominant_intensity, positivity)
        insight = await groq_service.get_daily_quote(context=dominant_emotion)

        # Build balanced sentiment breakdown
        sentiment_positive = emotions.get("joy", 0) + emotions.get("surprise", 0) * 0.3
        sentiment_negative = emotions.get("sadness", 0) + emotions.get("anger", 0) + emotions.get("fear", 0)
        sentiment_neutral = emotions.get("neutral", 0)
        sent_total = sentiment_positive + sentiment_negative + sentiment_neutral + 0.001

        analysis_result = {
            "emotions": emotions,
            "dominant_emotion": dominant_emotion,
            "dominant_intensity": dominant_intensity,
            "positivity": round(positivity, 3),
            "sentiment": {
                "positive": round(sentiment_positive / sent_total, 3),
                "neutral": round(sentiment_neutral / sent_total, 3),
                "negative": round(sentiment_negative / sent_total, 3)
            },
            "suggestions": suggestions,
            "insight": insight,
            "timestamp": datetime.now().isoformat(),
            "cached": False,
            "embeddings": [0.0] * 384
        }
        
        if emotions:
            self._cache[text_clean] = analysis_result
            
        return analysis_result
    
    async def analyze_image(self, image_bytes: bytes) -> Dict:
        """Analyze face emotions from an image using Hugging Face Vision API"""
        if not self.api_token:
            logger.warning("Hugging Face token missing. Skipping vision analysis.")
            return {"dominant_emotion": "neutral", "dominant_intensity": 0.0, "emotions": {}}
        
        headers = {"Authorization": f"Bearer {self.api_token}"}
        try:
            logger.info(f"Sending image to HF Vision API: {self.face_emotion_url}")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.face_emotion_url, 
                    headers=headers, 
                    content=image_bytes, 
                    timeout=20.0
                )
            
            if response.status_code == 200:
                results = response.json()
                logger.info(f"HF Vision API Success: {results}")
                if isinstance(results, list) and len(results) > 0:
                    # Handle both [{label: x, score: y}, ...] and [[{label: x, score: y}, ...]] formats
                    data = results[0] if isinstance(results[0], list) else results
                    emotions = {r['label'].lower(): r['score'] for r in data}
                    dominant_emotion = max(emotions, key=emotions.get)
                    dominant_intensity = emotions.get(dominant_emotion, 0)
                    
                    return {
                        "emotions": emotions,
                        "dominant_emotion": dominant_emotion,
                        "dominant_intensity": dominant_intensity,
                        "timestamp": datetime.now().isoformat()
                    }
            
            logger.error(f"HF Vision API Error ({response.status_code}): {response.text}")
            return {"dominant_emotion": "neutral", "dominant_intensity": 0.0, "emotions": {}, "error": response.text}
        except Exception as e:
            logger.error(f"Image analysis exception: {str(e)}")
            return {"dominant_emotion": "neutral", "dominant_intensity": 0.0, "emotions": {}, "error": str(e)}
    
    def _fallback_emotions(self, text: str) -> Dict[str, float]:
        """Keyword-based fallback with balanced defaults"""
        text = text.lower()
        if any(w in text for w in ["happy", "great", "amazing", "wonderful", "excited", "love"]): 
            return {"joy": 0.7, "neutral": 0.2, "sadness": 0.0, "anger": 0.0, "fear": 0.0, "surprise": 0.1}
        if any(w in text for w in ["sad", "crying", "depressed", "hopeless", "miserable"]): 
            return {"sadness": 0.7, "neutral": 0.1, "joy": 0.0, "anger": 0.1, "fear": 0.1, "surprise": 0.0}
        if any(w in text for w in ["angry", "mad", "furious", "hate", "rage"]): 
            return {"anger": 0.7, "neutral": 0.1, "joy": 0.0, "sadness": 0.1, "fear": 0.1, "surprise": 0.0}
        if any(w in text for w in ["scared", "afraid", "terrified", "anxious", "worried"]): 
            return {"fear": 0.6, "neutral": 0.2, "joy": 0.0, "sadness": 0.1, "anger": 0.0, "surprise": 0.1}
        # Default: neutral-heavy — prevents false sadness
        return {"neutral": 0.7, "joy": 0.1, "sadness": 0.05, "anger": 0.05, "fear": 0.05, "surprise": 0.05}

emotion_engine = EmotionDetectionEngine()
