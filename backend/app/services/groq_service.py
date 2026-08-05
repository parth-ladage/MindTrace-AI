import logging
import io
from typing import List, Dict, Any
from groq import AsyncGroq
from app.core.config import settings
from app.core.mlflow_config import log_llm_call, Timer

logger = logging.getLogger(__name__)

class GroqService:
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.client = None
        if self.api_key:
            self.client = AsyncGroq(api_key=self.api_key)
        else:
            logger.warning("GROQ_API_KEY not found. GroqService will be limited.")

    async def get_daily_quote(self, context: str = "general") -> str:
        """Generate an impressive wellness quote using Groq"""
        if not self.client:
            return "Believe in yourself. Every day is a new beginning."
        
        try:
            prompt = f"Generate a short, impressive, and futuristic wellness quote related to {context} for a mind tracking app called MindTrace AI+. Keep it under 20 words."

            with Timer() as timer:
                chat_completion = await self.client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama-3.3-70b-versatile",
                    max_tokens=50,
                )

            response_text = chat_completion.choices[0].message.content.strip().replace('"', '')
            log_llm_call(
                service_name="groq", model_name="llama-3.3-70b-versatile",
                function_name="get_daily_quote", prompt=prompt,
                response_text=response_text, latency_ms=timer.elapsed_ms,
                max_tokens=50,
            )
            return response_text
        except Exception as e:
            logger.error(f"Error generating quote with Groq: {e}")
            return "Your mind is your most powerful tool. Trace it well."

    async def get_personalized_suggestions(self, dominant_emotion: str, intensity: float, positivity: float) -> List[str]:
        """Generate personalized wellness suggestions with dynamic YouTube resource links"""
        if not self.client:
            return ["Practice mindful breathing.", "Stay hydrated.", "Take a short walk."]
        
        try:
            prompt = (
                f"Based on the following emotional state: dominant emotion: {dominant_emotion}, "
                f"intensity: {intensity*100}%, positivity: {positivity*100}%. "
                "Provide 3 personalized, actionable, and futuristic wellness suggestions for the MindTrace AI+ user. "
                "For EACH suggestion, also include a relevant YouTube search URL in parentheses at the end. "
                "Format the URL as: (https://www.youtube.com/results?search_query=<relevant+search+terms>) "
                "Return them as a simple list separated by newlines, no numbers."
            )

            with Timer() as timer:
                chat_completion = await self.client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama-3.3-70b-versatile",
                    max_tokens=250,
                )

            response_text = chat_completion.choices[0].message.content.strip()
            log_llm_call(
                service_name="groq", model_name="llama-3.3-70b-versatile",
                function_name="get_personalized_suggestions", prompt=prompt,
                response_text=response_text, latency_ms=timer.elapsed_ms,
                max_tokens=250,
                extra_params={"dominant_emotion": dominant_emotion, "intensity": intensity},
            )
            suggestions = response_text.split('\n')
            # Clean up and limit to 3
            return [s.strip('- ').strip() for s in suggestions if s.strip()][:3]
        except Exception as e:
            logger.error(f"Error generating suggestions with Groq: {e}")
            return ["Practice deep breathing for 5 minutes.", "Log your next positive interaction.", "Listen to calming frequency music."]

    async def get_ai_activities(self, user_data: dict, emotional_state: dict) -> List[dict]:
        """Generate highly personalized activities using Groq based on user profile and live emotions"""
        if not self.client:
            return [
                {"title": "Mindful Walk", "desc": "A quiet walk to clear your head.", "type": "activity"},
                {"title": "Creative Journaling", "desc": "Write down your thoughts.", "type": "activity"}
            ]
        
        try:
            interests = user_data.get("interests", [])
            age = user_data.get("age", "unknown")
            gender = user_data.get("gender", "unknown")
            dominant_emotion = emotional_state.get("dominant_emotion", "neutral")
            intensity = emotional_state.get("intensity", 0.5)
            escalation_level = emotional_state.get("escalation_level", "normal")
            
            interest_str = ", ".join(interests) if interests else "general wellness"
            
            prompt = (
                f"User Profile: Age {age}, Gender {gender}, Interests: {interest_str}. "
                f"Current Emotional State: Feeling {dominant_emotion} (intensity {intensity*100}%, state: {escalation_level}). "
                "Suggest 3 specific, unique, and highly personalized activities to help this user based on their specific interests and current mood. "
                "If they are stressed, suggest relaxing versions of their interests. If they are sad, suggest engaging versions. "
                "Format as JSON array of objects: [{\"title\": \"...\", \"desc\": \"...\", \"type\": \"...\"}] "
                "The 'type' should be one of: 'creative', 'physical', 'social', 'quiet', 'tech'. "
                "Only return the JSON list."
            )
            
            with Timer() as timer:
                chat_completion = await self.client.chat.completions.create(
                    messages=[{"role": "system", "content": "You are an advanced AI wellness coach for MindTrace AI+."},
                              {"role": "user", "content": prompt}],
                    model="llama-3.3-70b-versatile",
                    max_tokens=400,
                    response_format={"type": "json_object"}
                )
            
            import json
            content = chat_completion.choices[0].message.content
            log_llm_call(
                service_name="groq", model_name="llama-3.3-70b-versatile",
                function_name="get_ai_activities", prompt=prompt,
                response_text=content, latency_ms=timer.elapsed_ms,
                max_tokens=400,
                extra_params={"dominant_emotion": dominant_emotion},
            )
            data = json.loads(content)
            
            # Extract the list from potential root keys
            activities = []
            if isinstance(data, list):
                activities = data
            elif isinstance(data, dict):
                for key in data:
                    if isinstance(data[key], list):
                        activities = data[key]
                        break
            
            return activities[:3]
        except Exception as e:
            logger.error(f"Error generating AI activities: {e}")
            return [
                {"title": "Focused Breathing", "desc": "Regulate your nervous system.", "type": "quiet"},
                {"title": "Digital Detox", "desc": "Step away from screens for 15 minutes.", "type": "tech"}
            ]

    async def analyze_journal_sentiment(self, text: str, hf_context: dict = None):
        """
        Advanced Psychological Synthesis using Llama-3-70b.
        Combines raw NLP markers with deep contextual understanding to provide 
        extremely accurate emotional mapping.
        """
        system_prompt = """
        You are the MindTrace AI+ Core Synthesis Engine, a clinical-grade psychological analyzer.
        Your task is to analyze the provided journal text with maximum precision.
        
        CRITICAL ANTI-BIAS RULES:
        - Do NOT default to 'sadness' or 'anxiety' for normal, everyday text.
        - If the text describes routine activities, casual thoughts, or factual statements without strong emotional language, classify as 'Neutral'.
        - Only classify as a negative emotion if the text EXPLICITLY contains distressed, anguished, or strongly negative language.
        - Be especially careful not to over-diagnose. Neutral is a valid and common result.
        
        Advanced Methodology:
        1. Contextual Mapping: Don't just look for keywords. Understand the underlying tone and temporal stability of the user's state.
        2. Sentiment Decomposition: Distinguish between situational frustration and systemic distress.
        3. Multi-Factor Categorization: Map the text into one of these exact categories: 
           [Joy, Sadness, Anger, Fear, Anxiety, Surprise, Neutral, Frustration, Depressed, Lonely].
        
        Input Format: A user's journal entry.
        Output Format: STRICT JSON with keys:
        - dominant_emotion (string)
        - intensity (float 0.0 - 1.0)
        - suggestions (list of 3 precise, clinically-sound wellness protocols)
        - insight (a 1-sentence psychological synthesis of their current state)
        - escalation_score (float 0.0 - 1.0, probability of emotional crisis)
        """
        
        if not self.client:
            return {"dominant_emotion": "neutral", "intensity": 0.5, "suggestions": ["Record your thoughts more often."]}

        try:
            hf_hint = ""
            if hf_context:
                hf_hint = f"Initial neural network scan suggests: {hf_context.get('dominant_emotion')} with intensity {hf_context.get('intensity')}. Use this as baseline context but provide your own deeper analysis."
                
            prompt = (
                f"Analyze the following journal entry for deep emotional patterns, subtext, and underlying psychological states: \"{text}\"\n\n"
                f"{hf_hint}\n\n"
                "2. Calculate the 'intensity' of this emotion from 0.0 to 1.0 based on the extremity of the language used.\n"
                "3. Provide 3 highly personalized, actionable wellness suggestions tailored EXACTLY to the nuances of their entry.\n"
                "Format strictly as JSON: {\"dominant_emotion\": \"...\", \"intensity\": 0.0, \"suggestions\": [\"...\", \"...\", \"...\"]}"
            )

            with Timer() as timer:
                chat_completion = await self.client.chat.completions.create(
                    messages=[{"role": "system", "content": system_prompt},
                              {"role": "user", "content": prompt}],
                    model="llama-3.3-70b-versatile",
                    temperature=0.1, # Very low temperature for precise, deterministic classification
                    response_format={"type": "json_object"}
                )

            import json
            response_text = chat_completion.choices[0].message.content
            log_llm_call(
                service_name="groq", model_name="llama-3.3-70b-versatile",
                function_name="analyze_journal_sentiment",
                prompt=system_prompt + "\n" + prompt,
                response_text=response_text, latency_ms=timer.elapsed_ms,
                temperature=0.1,
            )
            return json.loads(response_text)
        except Exception as e:
            logger.error(f"Error in Groq sentiment analysis: {e}")
            return {"dominant_emotion": "neutral", "intensity": 0.5, "suggestions": ["Continue journaling to build patterns."]}

    async def get_place_suggestions(self, dominant_emotion: str, intensity: float, interests: List[str]) -> List[str]:
        """Suggest decompression places based on mood and interests"""
        if not self.client:
            return ["A quiet park.", "A cozy library.", "A local cafe."]
            
        try:
            interest_str = ", ".join(interests) if interests else "nature and peace"
            prompt = (
                f"User feeling {dominant_emotion} (intensity {intensity*100}%). "
                f"Interests: {interest_str}. "
                "Suggest 3 specific types of places or activities where this user could decompress. "
                "Return them as a simple list separated by newlines."
            )

            with Timer() as timer:
                chat_completion = await self.client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt}],
                    model="llama-3.3-70b-versatile",
                    max_tokens=100,
                )

            response_text = chat_completion.choices[0].message.content.strip()
            log_llm_call(
                service_name="groq", model_name="llama-3.3-70b-versatile",
                function_name="get_place_suggestions", prompt=prompt,
                response_text=response_text, latency_ms=timer.elapsed_ms,
                max_tokens=100,
                extra_params={"dominant_emotion": dominant_emotion},
            )
            places = response_text.split('\n')
            return [p.strip('- ').strip() for p in places if p.strip()][:3]
        except Exception as e:
            logger.error(f"Error in Groq place suggestions: {e}")
            return ["A peaceful garden.", "A quiet museum.", "A scenic viewpoint."]

    async def _call_llm(self, system_message: str, user_message: str) -> str:
        """Generic helper for LLM chat completions"""
        if not self.client:
            return "I am processing your thoughts, but I need a moment to connect."
            
        try:
            with Timer() as timer:
                chat_completion = await self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_message},
                        {"role": "user", "content": user_message}
                    ],
                    model="llama-3.3-70b-versatile",
                    max_tokens=250,
                    temperature=0.7
                )

            response_text = chat_completion.choices[0].message.content.strip()
            log_llm_call(
                service_name="groq", model_name="llama-3.3-70b-versatile",
                function_name="_call_llm",
                prompt=system_message + "\n" + user_message,
                response_text=response_text, latency_ms=timer.elapsed_ms,
                temperature=0.7, max_tokens=250,
            )
            return response_text
        except Exception as e:
            logger.error(f"LLM Call Error: {e}")
            return "I'm still here with you. Let's just breathe for a moment."

    # ========================
    # EXPANSION 1: Audio/Voice Emotion Detection via Whisper
    # ========================
    async def transcribe_audio(self, audio_bytes: bytes, filename: str = "audio.wav") -> Dict[str, Any]:
        """
        Transcribe audio using Groq's Whisper model.
        Returns the transcribed text for further emotion analysis.
        """
        if not self.client:
            return {"text": "", "error": "Groq client not initialized"}
        
        try:
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = filename

            with Timer() as timer:
                transcription = await self.client.audio.transcriptions.create(
                    file=(filename, audio_file),
                    model="whisper-large-v3",
                    language="en",
                    response_format="verbose_json"
                )

            text = transcription.text
            duration = getattr(transcription, 'duration', None)

            log_llm_call(
                service_name="groq", model_name="whisper-large-v3",
                function_name="transcribe_audio",
                prompt=f"[audio_transcription:{filename}]",
                response_text=text,
                latency_ms=timer.elapsed_ms,
                extra_params={
                    "audio_size_bytes": len(audio_bytes),
                    "filename": filename,
                    "audio_duration": duration if duration else "unknown",
                    "transcription_length": len(text) if text else 0,
                },
            )
            
            return {
                "text": text,
                "duration": duration,
                "language": getattr(transcription, 'language', 'en')
            }
        except Exception as e:
            logger.error(f"Audio transcription error: {e}")
            return {"text": "", "error": str(e)}

    # ========================
    # EXPANSION 2: Weekly Emotional Synthesis
    # ========================
    async def generate_weekly_synthesis(self, emotion_summary: Dict, journal_snippets: List[str]) -> Dict[str, Any]:
        """
        Generate a comprehensive weekly emotional synthesis report.
        Takes aggregated emotion data + journal snippets and produces:
        - Overall trend analysis
        - Behavioral patterns detected
        - Long-term recommendations
        - Risk assessment
        """
        if not self.client:
            return {
                "trend": "stable",
                "summary": "Not enough data for weekly analysis.",
                "patterns": [],
                "recommendations": ["Continue journaling daily."],
                "risk_level": "low"
            }
        
        try:
            snippets_text = "\n".join([f"- {s[:200]}" for s in journal_snippets[:10]])
            
            prompt = (
                f"Analyze this user's emotional week for MindTrace AI+.\n\n"
                f"Emotion Distribution: {emotion_summary}\n\n"
                f"Journal Excerpts:\n{snippets_text}\n\n"
                "Provide a comprehensive weekly synthesis as strict JSON with these keys:\n"
                "- trend: one of 'improving', 'stable', 'declining'\n"
                "- summary: 2-3 sentence overview of their emotional week\n"
                "- patterns: list of 2-3 behavioral patterns detected\n"
                "- recommendations: list of 3 specific, actionable long-term recommendations\n"
                "- risk_level: one of 'low', 'moderate', 'high'\n"
                "- highlight: the single most positive moment from the week\n"
                "Only return the JSON."
            )
            
            system_msg = "You are an expert behavioral psychologist providing weekly emotional synthesis for the MindTrace AI+ platform. Be objective and balanced."

            with Timer() as timer:
                chat_completion = await self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": prompt}
                    ],
                    model="llama-3.3-70b-versatile",
                    max_tokens=500,
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
            
            import json
            response_text = chat_completion.choices[0].message.content
            log_llm_call(
                service_name="groq", model_name="llama-3.3-70b-versatile",
                function_name="generate_weekly_synthesis",
                prompt=system_msg + "\n" + prompt,
                response_text=response_text, latency_ms=timer.elapsed_ms,
                temperature=0.3, max_tokens=500,
            )
            return json.loads(response_text)
        except Exception as e:
            logger.error(f"Weekly synthesis error: {e}")
            return {
                "trend": "stable",
                "summary": "Unable to generate synthesis at this time.",
                "patterns": [],
                "recommendations": ["Continue your daily journaling practice."],
                "risk_level": "low"
            }

groq_service = GroqService()
