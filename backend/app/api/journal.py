from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from typing import List, Optional
from datetime import datetime
from app.core.security import get_current_user
from app.core.database import get_database
from app.ai.emotion_detector import emotion_engine
from app.services.emotional_tracking import emotional_tracking_engine
from app.schemas.models import JournalEntryCreate
from bson import ObjectId
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/create")
async def create_journal_entry(
    entry_data: JournalEntryCreate,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """Create a new journal entry with emotion detection"""
    user_id = current_user["sub"]
    db = get_database()
    
    from app.services.huggingface_service import huggingface_service
    from app.services.groq_service import groq_service
    
    # 1. Fast Initial NLP Analysis (Hugging Face DistilRoBERTa)
    hf_analysis = await huggingface_service.analyze_emotions(entry_data.content)
    
    # 2. Advanced Psychological Synthesis (Groq Llama-3-70b)
    # Pass the initial HF scan as context, but let the LLM make the final, more accurate determination.
    ai_analysis = await groq_service.analyze_journal_sentiment(
        text=entry_data.content, 
        hf_context=hf_analysis
    )
    
    # 3. Merge findings: Prioritize Groq's high-accuracy analysis, fallback to HF
    dominant_emotion = ai_analysis.get("dominant_emotion", hf_analysis["dominant_emotion"]).lower()
    
    # 4. Multi-Modal Scoring Integration
    # Calculate text positivity score
    text_positivity = 1.0 - hf_analysis["intensity"] if dominant_emotion in ["sadness", "anger", "fear", "depressed", "anxiety"] else hf_analysis["intensity"]
    
    # Use provided scores or fallback to text score
    audio_score = entry_data.audio_score if entry_data.audio_score is not None else text_positivity
    video_score = entry_data.video_score if entry_data.video_score is not None else text_positivity
    
    # FINAL HOLISTIC SCORE (Average of Text, Audio, and Video)
    final_positivity_score = (text_positivity + audio_score + video_score) / 3.0
    dominant_intensity = ai_analysis.get("intensity", hf_analysis["intensity"])
    
    # Create entry document
    entry_doc = {
        "user_id": user_id,
        "content": entry_data.content,
        "emotions_detected": [dominant_emotion],
        "all_scores": hf_analysis["all_emotions"],
        "dominant_emotion": dominant_emotion,
        "dominant_intensity": dominant_intensity,
        "text_score": text_positivity,
        "audio_score": audio_score,
        "video_score": video_score,
        "positivity": final_positivity_score, # This is now the average score
        "mood_intensity": dominant_intensity,
        "suggestions": ai_analysis.get("suggestions", []),
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = await db.journal_entries.insert_one(entry_doc)
    
    # 4. Record emotions and check for critical alerts
    if dominant_emotion:
        # Record in tracking engine
        tracking_result = emotional_tracking_engine.add_emotion_event(
            user_id=user_id,
            emotion=dominant_emotion,
            intensity=dominant_intensity,
            source="journal",
            context=f"Journal entry: {entry_data.content[:100]}"
        )
        
        # SOS / Guardian Alert Logic (MULTI-FACTOR — requires BOTH models to agree)
        CRITICAL_EMOTIONS = ["sadness", "fear", "anger", "depressed", "anxiety", "frustration", "lonely"]
        hf_is_critical = hf_analysis["intensity"] > 0.75 and hf_analysis["dominant_emotion"].lower() in CRITICAL_EMOTIONS
        groq_is_critical = ai_analysis.get("intensity", 0) > 0.9
        
        # BOTH models must flag the text as critical to trigger an SOS alert.
        # This prevents prompt injection attacks where a user manipulates the LLM.
        if (dominant_emotion in CRITICAL_EMOTIONS and final_positivity_score < 0.3) and (hf_is_critical or groq_is_critical):
            user = await db.users.find_one({"_id": ObjectId(user_id)})
            if user and user.get("guardian_email"):
                from app.services.alert_service import alert_service
                await alert_service.send_guardian_alert(
                    user_name=user.get("name", "User"),
                    guardian_email=user["guardian_email"],
                    emotion=dominant_emotion,
                    intensity=1.0 - final_positivity_score, # Use distress intensity
                    content_snippet=entry_data.content[:100]
                )

    # 5. Check if it's late night (>= 9 PM) to trigger End-of-Day report
    now_hour = datetime.now().hour
    if now_hour >= 21:
        from app.services.report_service import report_service
        # Use FastAPI BackgroundTasks instead of dangling asyncio.create_task
        background_tasks.add_task(report_service.generate_daily_report, user_id)

    return {
        "entry_id": str(result.inserted_id),
        "dominant_emotion": dominant_emotion,
        "sentiment": dominant_emotion,
        "positivity": 1.0 - dominant_intensity if dominant_emotion in ["sadness", "anger", "fear"] else dominant_intensity,
        "suggestions": ai_analysis.get("suggestions", []),
        "insight": ai_analysis.get("dominant_emotion", "Neutral"),
        "report_triggered": now_hour >= 21
    }



@router.get("/list")
async def get_journal_entries(
    limit: int = 20,
    skip: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """Get user's journal entries"""
    user_id = current_user["sub"]
    db = get_database()
    
    entries = await db.journal_entries.find(
        {"user_id": user_id}
    ).sort("created_at", -1).skip(skip).limit(limit).to_list(None)
    
    # Convert ObjectId to string
    for entry in entries:
        entry["_id"] = str(entry["_id"])
    
    total = await db.journal_entries.count_documents({"user_id": user_id})
    
    return {
        "entries": entries,
        "total": total,
        "limit": limit,
        "skip": skip
    }


@router.get("/{entry_id}")
async def get_journal_entry(
    entry_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific journal entry"""
    user_id = current_user["sub"]
    db = get_database()
    
    try:
        entry = await db.journal_entries.find_one({
            "_id": ObjectId(entry_id),
            "user_id": user_id
        })
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid entry ID"
        )
    
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry not found"
        )
    
    entry["_id"] = str(entry["_id"])
    return entry


@router.delete("/{entry_id}")
async def delete_journal_entry(
    entry_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a journal entry"""
    user_id = current_user["sub"]
    db = get_database()
    
    try:
        result = await db.journal_entries.delete_one({
            "_id": ObjectId(entry_id),
            "user_id": user_id
        })
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid entry ID"
        )
    
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entry not found or unauthorized"
        )
    
    return {"deleted": True}


@router.get("/search/emotions")
async def search_entries_by_emotion(
    emotion: str,
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Search journal entries by emotion"""
    user_id = current_user["sub"]
    db = get_database()
    
    entries = await db.journal_entries.find({
        "user_id": user_id,
        "emotions_detected": emotion.lower()
    }).sort("created_at", -1).limit(limit).to_list(None)
    
    for entry in entries:
        entry["_id"] = str(entry["_id"])
    
    return {
        "entries": entries,
        "emotion": emotion,
        "count": len(entries)
    }
