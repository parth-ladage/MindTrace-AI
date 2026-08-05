from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional
from datetime import datetime
from app.core.security import get_current_user
from app.core.database import get_database
from app.services.emotional_tracking import emotional_tracking_engine
from app.services.scoring_engine import scoring_engine
from app.services.intervention_engine import intervention_engine
from app.websocket.manager import manager
from bson import ObjectId
import logging

from app.services.gemini_service import gemini_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/recommend")
async def get_recommended_interventions(
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get recommended interventions based on current emotional state and AI suggestions"""
    user_id = current_user["sub"]
    db = get_database()
    
    # Get user onboarding data
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    user_data = {
        "interests": user.get("interests", []),
        "age": user.get("age"),
        "gender": user.get("gender")
    }
    
    # Get current escalation pattern
    escalation = emotional_tracking_engine.detect_escalation_patterns(user_id)
    
    # Get AI personalized activities based on mood and onboarding data
    emotional_state = {
        "dominant_emotion": escalation["trigger_emotions"][0] if escalation["trigger_emotions"] else "calm",
        "intensity": escalation["escalation_score"],
        "escalation_level": escalation["escalation_level"]
    }
    
    ai_activities = await gemini_service.get_ai_activities(user_data, emotional_state)
    
    # Get user's safe links
    safe_links = await db.user_safe_links.find({"user_id": user_id}).to_list(5)
    
    # Get recent intervention effectiveness
    recent_logs = await db.intervention_logs.find(
        {"user_id": user_id}
    ).sort("timestamp", -1).limit(10).to_list(None)
    
    effectiveness_map = {}
    for log in recent_logs:
        intervention_type = log.get("intervention_type")
        effectiveness = log.get("effectiveness", 0.5)
        if intervention_type not in effectiveness_map:
            effectiveness_map[intervention_type] = effectiveness
    
    # Get standard recommendations
    recommendations = intervention_engine.recommend_interventions(
        escalation_pattern=escalation,
        user_safe_links=safe_links,
        recent_effectiveness=effectiveness_map,
        lat=lat,
        lng=lng
    )
    
    # Merge AI activities into recommendations
    for activity in ai_activities:
        recommendations.append({
            "type_id": f"ai_activity_{activity['type']}",
            "title": activity["title"],
            "description": activity["desc"],
            "type": activity["type"],
            "is_ai": True
        })
    
    return {
        "interventions": recommendations,
        "escalation_level": escalation["escalation_level"],
        "escalation_score": escalation["escalation_score"],
        "ai_generated": True
    }


@router.get("/sequence")
async def get_intervention_sequence(
    current_user: dict = Depends(get_current_user)
):
    """Get complete intervention workflow sequence"""
    user_id = current_user["sub"]
    db = get_database()
    
    # Get escalation pattern
    escalation = emotional_tracking_engine.detect_escalation_patterns(user_id)
    
    # Get safe links
    safe_links = await db.user_safe_links.find({"user_id": user_id}).to_list(5)
    
    # Generate sequence
    sequence = intervention_engine.generate_intervention_sequence(
        escalation_pattern=escalation,
        user_safe_links=safe_links
    )
    
    return sequence


@router.post("/trigger/{intervention_type}")
async def trigger_intervention(
    intervention_type: str,
    current_user: dict = Depends(get_current_user)
):
    """Trigger a specific intervention"""
    user_id = current_user["sub"]
    db = get_database()
    
    # Log intervention
    log_entry = {
        "user_id": user_id,
        "intervention_type": intervention_type,
        "timestamp": datetime.utcnow(),
        "effectiveness": None,
        "user_feedback": None,
        "trigger_emotion": None
    }
    
    result = await db.intervention_logs.insert_one(log_entry)
    
    # Broadcast intervention triggered
    intervention_data = intervention_engine.interventions.get(intervention_type, {})
    await manager.broadcast_intervention_triggered(
        user_id=user_id,
        intervention={
            "type_id": intervention_type,
            "title": intervention_data.get("title", intervention_type),
            "description": intervention_data.get("description", ""),
            "duration": intervention_data.get("duration_seconds")
        }
    )
    
    return {
        "intervention_triggered": True,
        "intervention_type": intervention_type,
        "log_id": str(result.inserted_id)
    }


@router.post("/feedback/{log_id}")
async def submit_intervention_feedback(
    log_id: str,
    effectiveness: float,
    feedback: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Submit feedback on intervention effectiveness"""
    user_id = current_user["sub"]
    db = get_database()
    
    from bson import ObjectId
    
    try:
        # Update intervention log with effectiveness
        result = await db.intervention_logs.update_one(
            {
                "_id": ObjectId(log_id),
                "user_id": user_id
            },
            {
                "$set": {
                    "effectiveness": max(0.0, min(1.0, effectiveness)),
                    "user_feedback": feedback,
                    "feedback_timestamp": datetime.utcnow()
                }
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Intervention log not found"
            )
        
        return {
            "feedback_recorded": True,
            "effectiveness": effectiveness
        }
    
    except Exception as e:
        logger.error(f"Error updating feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid intervention log ID"
        )


@router.get("/coping-strategies")
async def get_coping_strategies(
    current_user: dict = Depends(get_current_user)
):
    """Get personalized coping strategies"""
    user_id = current_user["sub"]
    db = get_database()
    
    # Get emotional history
    from datetime import timedelta
    cutoff_time = datetime.utcnow() - timedelta(days=30)
    
    emotional_events = await db.realtime_emotion_events.find({
        "user_id": user_id,
        "timestamp": {"$gt": cutoff_time}
    }).to_list(None)
    
    # Get past interventions
    past_interventions = await db.intervention_logs.find({
        "user_id": user_id,
        "timestamp": {"$gt": cutoff_time}
    }).to_list(None)
    
    # Generate strategies
    strategies = intervention_engine.suggest_coping_strategies(
        emotional_history=emotional_events,
        past_interventions=past_interventions
    )
    
    return {
        "strategies": strategies,
        "personalized": len(emotional_events) > 0
    }


@router.post("/recovery-session/start")
async def start_recovery_session(
    current_user: dict = Depends(get_current_user)
):
    """Start a recovery session after emotional escalation"""
    user_id = current_user["sub"]
    db = get_database()
    
    # Create recovery session
    session_doc = {
        "user_id": user_id,
        "started_at": datetime.utcnow(),
        "ended_at": None,
        "interventions": [],
        "effectiveness": None
    }
    
    result = await db.recovery_sessions.insert_one(session_doc)
    
    # Reset escalation tracking
    emotional_tracking_engine.reset_user_tracking(user_id)
    
    return {
        "session_id": str(result.inserted_id),
        "started": True
    }


@router.post("/recovery-session/{session_id}/complete")
async def complete_recovery_session(
    session_id: str,
    effectiveness: float,
    current_user: dict = Depends(get_current_user)
):
    """Complete a recovery session and record effectiveness"""
    user_id = current_user["sub"]
    db = get_database()
    
    from bson import ObjectId
    
    try:
        result = await db.recovery_sessions.update_one(
            {
                "_id": ObjectId(session_id),
                "user_id": user_id
            },
            {
                "$set": {
                    "ended_at": datetime.utcnow(),
                    "effectiveness": max(0.0, min(1.0, effectiveness))
                }
            }
        )
        
        if result.matched_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recovery session not found"
            )
        
        return {
            "session_completed": True,
            "effectiveness": effectiveness
        }
    
    except Exception as e:
        logger.error(f"Error completing recovery session: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID"
        )
