import logging
from typing import List, Dict, Any
from app.services.gemini_service import gemini_service
from app.core.database import get_database
from app.services.emotional_tracking import emotional_tracking_engine

logger = logging.getLogger(__name__)

class CompanionService:
    """
    Empathetic AI Companion Service
    Fine-tuned for humanized emotional support based on real-time biometric data.
    """
    
    SYSTEM_PROMPT = """
    You are 'Aria', the MindTrace Companion. You are a deeply empathetic friend who senses the user's mood through the screen.
    
    CORE PERSONALITY:
    - Warm, nurturing, and highly conversational.
    - NEVER use technical words like 'biometrics' or 'data'.
    
    REQUIREMENTS:
    1. Directly address the exact problem the user mentioned.
    2. Validate their specific feelings logically.
    3. Offer warm reassurance and gently guide them toward a positive thought.
    4. Your response MUST be exactly 3 to 4 complete, well-formed sentences. DO NOT cut off mid-sentence.
    
    EXAMPLE GOOD RESPONSE:
    "I can completely understand why you'd be second-guessing yourself; it's so normal to feel a bit of imposter syndrome before a big presentation. Remember that you were chosen to do this because you know your material better than anyone else in that room. Take a deep breath with me—you are going to do absolutely wonderfully tomorrow."
    """

    async def chat_with_companion(self, user_id: str, user_message: str) -> Dict[str, Any]:
        """
        Generate a humanized response based on the user's live emotional state.
        """
        db = get_database()
        
        # 1. Fetch Live Emotional State
        current_emotion = emotional_tracking_engine.get_dominant_emotion(user_id) or "neutral"
        escalation = emotional_tracking_engine.detect_escalation_patterns(user_id)
        intensity = escalation.get("score", 0.5)
            
        # 2. Construct the specialized context
        context = f"User's Live State: {current_emotion.upper()} (Intensity: {intensity}). "
        
        # 3. Call LLM with specialized prompt
        prompt = f"{context}\nUser says: {user_message}"
        
        response_text = await gemini_service._call_llm(
            system_message=self.SYSTEM_PROMPT,
            user_message=prompt
        )
        
        # 4. Log the interaction for report synthesis
        await db.chat_history.insert_one({
            "user_id": user_id,
            "message": user_message,
            "response": response_text,
            "detected_emotion": current_emotion,
            "timestamp": datetime.utcnow()
        })
        
        return {
            "response": response_text,
            "detected_emotion": current_emotion,
            "intensity": intensity
        }

from datetime import datetime
companion_service = CompanionService()
