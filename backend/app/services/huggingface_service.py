import aiohttp
import logging
from app.core.config import settings
from app.core.mlflow_config import log_hf_inference, Timer

logger = logging.getLogger(__name__)

class HuggingFaceService:
    """
    Service to interact with Hugging Face Inference API for high-accuracy NLP analysis.
    Using 'j-hartmann/emotion-english-distilroberta-base' for fine-tuned emotion detection.
    """
    
    API_URL = "https://api-inference.huggingface.co/models/j-hartmann/emotion-english-distilroberta-base"
    
    def __init__(self):
        self.api_key = settings.HUGGINGFACE_TOKEN
        if not self.api_key:
            logger.warning("HUGGINGFACE_TOKEN not found. HuggingFaceService will be limited.")

    async def analyze_emotions(self, text: str) -> dict:
        """
        Detects 7 fine-tuned emotions: anger, disgust, fear, joy, neutral, sadness, surprise.
        """
        if not self.api_key:
            return {"dominant_emotion": "neutral", "intensity": 0.5, "all_emotions": {}}

        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"inputs": text}

        try:
            with Timer() as timer:
                async with aiohttp.ClientSession() as session:
                    async with session.post(self.API_URL, headers=headers, json=payload) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            logger.error(f"Hugging Face API error: {error_text}")
                            return {"dominant_emotion": "neutral", "intensity": 0.5, "all_emotions": {}}
                        
                        data = await response.json()

            # Hugging Face returns a list of lists of objects: [[{"label": "...", "score": ...}, ...]]
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                results = data[0]
                # Find dominant
                dominant = max(results, key=lambda x: x['score'])
                all_emotions = {r['label']: r['score'] for r in results}
                
                result = {
                    "dominant_emotion": dominant['label'],
                    "intensity": dominant['score'],
                    "all_emotions": all_emotions
                }

                # Log the HuggingFace inference call
                log_hf_inference(
                    model_name="j-hartmann/emotion-english-distilroberta-base",
                    input_text=text,
                    result={
                        "dominant_emotion": dominant['label'],
                        "dominant_intensity": dominant['score'],
                    },
                    latency_ms=timer.elapsed_ms,
                )

                return result
            
            return {"dominant_emotion": "neutral", "intensity": 0.5, "all_emotions": {}}
        except Exception as e:
            logger.error(f"Hugging Face Request failed: {e}")
            return {"dominant_emotion": "neutral", "intensity": 0.5, "all_emotions": {}}

huggingface_service = HuggingFaceService()
