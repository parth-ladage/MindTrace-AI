from fastapi import APIRouter, Depends, WebSocket, HTTPException, status, UploadFile, File
from typing import List, Optional
from datetime import datetime
from app.core.security import get_current_user
from app.core.database import get_database
from app.ai.emotion_detector import emotion_engine
from app.services.emotional_tracking import emotional_tracking_engine
from app.services.scoring_engine import scoring_engine
from app.services.intervention_engine import intervention_engine
from app.services.groq_service import groq_service
from app.schemas.models import EmotionEventCreate, EmotionEvent
from app.websocket.manager import manager
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


from pydantic import BaseModel

class TextAnalysisRequest(BaseModel):
    text: str

@router.post("/detect")
async def detect_emotion(
    request: TextAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Detect emotions from text input.
    This is called from journaling, chat, or other text input.
    """
    user_id = current_user["sub"]
    
    # Analyze text
    analysis = await emotion_engine.analyze_text_comprehensive(request.text)
    
    return {
        "emotions": analysis["emotions"],
        "dominant_emotion": analysis["dominant_emotion"],
        "dominant_intensity": analysis["dominant_intensity"],
        "sentiment": analysis["sentiment"],
        "positivity": analysis["positivity"],
        "suggestions": analysis.get("suggestions", []),
        "insight": analysis.get("insight", "")
    }


class FaceAnalysisRequest(BaseModel):
    image: str  # Base64 string

@router.post("/detect-face")
async def detect_face_emotion(
    request: FaceAnalysisRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Detect emotions from a camera frame (base64 image).
    """
    user_id = current_user["sub"]
    
    # Decode base64 image
    import base64
    try:
        if "," in request.image:
            header, encoded = request.image.split(",", 1)
        else:
            encoded = request.image
        
        image_bytes = base64.b64decode(encoded)
    except Exception as e:
        logger.error(f"Base64 decode error: {e}")
        raise HTTPException(status_code=400, detail="Invalid image data")
    
    # Analyze image
    analysis = await emotion_engine.analyze_image(image_bytes)
    
    # Record event automatically if intensity is significant
    # Lowered threshold to 0.1 for more "live" feeling on dashboard
    if analysis["dominant_intensity"] > 0.1:
        # 1. Add to tracking engine (in-memory)
        emotional_tracking_engine.add_emotion_event(
            user_id=user_id,
            emotion=analysis["dominant_emotion"],
            intensity=analysis["dominant_intensity"],
            source="camera"
        )
        
        # 2. Store in MongoDB (persistent)
        db = get_database()
        await db.realtime_emotion_events.insert_one({
            "user_id": user_id,
            "emotion": analysis["dominant_emotion"],
            "intensity": analysis["dominant_intensity"],
            "source": "camera",
            "timestamp": datetime.utcnow()
        })
        
        # 3. Broadcast update
        await manager.broadcast_emotional_update(
            user_id=user_id,
            emotion=analysis["dominant_emotion"],
            intensity=analysis["dominant_intensity"],
            escalation_score=emotional_tracking_engine.escalation_scores.get(user_id, 0.0),
            is_critical=emotional_tracking_engine.escalation_scores.get(user_id, 0.0) >= settings.CRITICAL_THRESHOLD
        )

        # 4. Check for Escalation and alert
        escalation_pattern = emotional_tracking_engine.detect_escalation_patterns(user_id)
        if escalation_pattern["is_escalating"]:
            # Get AI interventions from engine
            from app.services.intervention_engine import intervention_engine
            interventions = intervention_engine.recommend_interventions(
                escalation_pattern=escalation_pattern,
                user_safe_links=[] # Can be fetched from DB if needed
            )
            
            await manager.broadcast_escalation_alert(
                user_id=user_id,
                escalation_pattern=escalation_pattern,
                recommended_interventions=interventions
            )

    return analysis


# ========================
# EXPANSION 1: Audio/Voice Emotion Detection
# ========================
@router.post("/detect-audio")
async def detect_audio_emotion(
    audio: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Detect emotions from an audio recording.
    1. Transcribes audio using Groq Whisper
    2. Runs emotion analysis on the transcript
    3. Records the event and returns multi-modal results
    """
    user_id = current_user["sub"]
    
    # Validate file type
    allowed_types = ["audio/wav", "audio/mpeg", "audio/mp3", "audio/webm", "audio/ogg", "audio/mp4", "audio/m4a"]
    if audio.content_type and audio.content_type not in allowed_types:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported audio format: {audio.content_type}. Supported: wav, mp3, webm, ogg, m4a"
        )
    
    # Read audio bytes
    audio_bytes = await audio.read()
    if len(audio_bytes) < 1000:
        raise HTTPException(status_code=400, detail="Audio file too small. Please record at least 1 second.")
    
    # Step 1: Transcribe audio using Whisper
    transcription = await groq_service.transcribe_audio(audio_bytes, filename=audio.filename or "audio.wav")
    
    if not transcription.get("text"):
        return {
            "transcription": "",
            "emotions": {},
            "dominant_emotion": "neutral",
            "dominant_intensity": 0.0,
            "error": transcription.get("error", "Could not transcribe audio. Try speaking more clearly.")
        }
    
    transcript_text = transcription["text"]
    
    # Step 2: Analyze emotions from transcript
    analysis = await emotion_engine.analyze_text_comprehensive(transcript_text)
    
    # Step 3: Record the emotion event
    db = get_database()
    dominant_emotion = analysis["dominant_emotion"]
    dominant_intensity = analysis["dominant_intensity"]
    
    if dominant_intensity > 0.1:
        emotional_tracking_engine.add_emotion_event(
            user_id=user_id,
            emotion=dominant_emotion,
            intensity=dominant_intensity,
            source="voice"
        )
        
        await db.realtime_emotion_events.insert_one({
            "user_id": user_id,
            "emotion": dominant_emotion,
            "intensity": dominant_intensity,
            "source": "voice",
            "transcript": transcript_text[:500],
            "timestamp": datetime.utcnow()
        })
    
    return {
        "transcription": transcript_text,
        "duration": transcription.get("duration"),
        "language": transcription.get("language", "en"),
        "emotions": analysis["emotions"],
        "dominant_emotion": dominant_emotion,
        "dominant_intensity": dominant_intensity,
        "positivity": analysis["positivity"],
        "sentiment": analysis["sentiment"],
        "suggestions": analysis.get("suggestions", []),
        "insight": analysis.get("insight", "")
    }


@router.post("/record")
async def record_emotion(
    emotion_event: EmotionEventCreate,
    current_user: dict = Depends(get_current_user)
):
    """
    Record an emotion event and trigger escalation detection if needed.
    """
    user_id = current_user["sub"]
    db = get_database()
    
    # Add to tracking engine
    tracking_result = emotional_tracking_engine.add_emotion_event(
        user_id=user_id,
        emotion=emotion_event.emotion,
        intensity=emotion_event.intensity,
        source=emotion_event.source,
        context=emotion_event.context
    )
    
    # Store in database
    event_doc = emotion_event.dict()
    event_doc["user_id"] = user_id
    event_doc["timestamp"] = datetime.utcnow()
    
    result = await db.realtime_emotion_events.insert_one(event_doc)
    
    # Check for escalation
    escalation_pattern = emotional_tracking_engine.detect_escalation_patterns(user_id)
    
    # Broadcast emotional update
    await manager.broadcast_emotional_update(
        user_id=user_id,
        emotion=emotion_event.emotion,
        intensity=emotion_event.intensity,
        escalation_score=tracking_result.get("escalation_score", 0.0),
        is_critical=escalation_pattern.get("critical", False)
    )
    
    # If escalating or critical, trigger interventions
    is_escalating = escalation_pattern.get("critical", False) or escalation_pattern.get("escalation_level") in ("high", "critical")
    if is_escalating:
        # Get user's safe links
        safe_links = await db.user_safe_links.find({"user_id": user_id}).to_list(5)
        
        # Get recommended interventions
        recommendations = intervention_engine.recommend_interventions(
            escalation_pattern=escalation_pattern,
            user_safe_links=safe_links
        )
        
        # Broadcast alert
        await manager.broadcast_escalation_alert(
            user_id=user_id,
            escalation_pattern=escalation_pattern,
            recommended_interventions=recommendations
        )
        
        # Store intervention log
        await db.intervention_logs.insert_one({
            "user_id": user_id,
            "intervention_type": "escalation_alert",
            "trigger_emotion": emotion_event.emotion,
            "timestamp": datetime.utcnow(),
            "effectiveness": None,
            "user_feedback": None
        })
    
    return {
        "event_recorded": True,
        "event_id": str(result.inserted_id),
        "escalation": tracking_result,
        "is_escalating": is_escalating,
        "escalation_level": escalation_pattern.get("escalation_level", "normal")
    }


@router.get("/history")
async def get_emotion_history(
    hours: int = 24,
    current_user: dict = Depends(get_current_user)
):
    """Get emotion event history"""
    user_id = current_user["sub"]
    db = get_database()
    
    from datetime import timedelta
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    events = await db.realtime_emotion_events.find({
        "user_id": user_id,
        "timestamp": {"$gt": cutoff_time}
    }).sort("timestamp", -1).limit(500).to_list(500)
    
    # Serialize ObjectIds
    for e in events:
        if "_id" in e:
            e["_id"] = str(e["_id"])
    
    return {
        "events": events,
        "count": len(events),
        "period_hours": hours
    }


@router.get("/statistics")
async def get_emotion_statistics(
    hours: int = 24,
    current_user: dict = Depends(get_current_user)
):
    """Get emotional statistics"""
    user_id = current_user["sub"]
    
    # Get events from tracking engine
    from app.services.emotional_tracking import emotional_tracking_engine
    stats = emotional_tracking_engine.get_emotional_stats(user_id, hours=hours // 24)
    
    return stats


@router.get("/status")
async def get_emotional_status(
    current_user: dict = Depends(get_current_user)
):
    """Get current emotional status and escalation level"""
    user_id = current_user["sub"]
    
    escalation = emotional_tracking_engine.detect_escalation_patterns(user_id)
    
    return {
        "escalation_level": escalation["escalation_level"],
        "escalation_score": escalation["escalation_score"],
        "is_escalating": escalation["is_escalating"],
        "is_critical": escalation["critical"],
        "trigger_emotions": escalation["trigger_emotions"],
        "recent_event_frequency": escalation["event_frequency"]
    }


@router.websocket("/stream/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """
    WebSocket endpoint for real-time emotional tracking.
    Requires an access token passed either via the `Authorization` header
    (Bearer token) or as a `token` query parameter. The token payload's
    `sub` field must match the `user_id` path parameter.
    """
    # Accept the connection only after verifying token
    try:
        # Try header first (standard) then query param
        auth_header = websocket.headers.get('authorization')
        token = None
        if auth_header and auth_header.lower().startswith('bearer '):
            token = auth_header.split(' ', 1)[1]
        else:
            token = websocket.query_params.get('token')

        if not token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        # Verify token and ensure it belongs to the requested user_id
        from app.core.security import verify_token

        try:
            payload = verify_token(token)
        except Exception as e:
            logger.warning("WebSocket auth failed: %s", e)
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        token_user = payload.get('sub')
        if token_user != user_id:
            logger.warning("WebSocket token user mismatch: %s != %s", token_user, user_id)
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        logger.info("WebSocket auth successful for user %s", user_id)

        await manager.connect(websocket, user_id)

        try:
            while True:
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            manager.disconnect(websocket, user_id)

    except Exception as outer_e:
        logger.exception("Unhandled websocket error: %s", outer_e)
        try:
            await websocket.close()
        except Exception:
            pass
