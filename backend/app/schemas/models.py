from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class AuthSignupRequest(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None
    username: Optional[str] = None
    name: Optional[str] = None
    guardian_email: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    interests: Optional[List[str]] = []


class AuthLoginRequest(BaseModel):
    email: str
    password: str


# User Models
class UserBase(BaseModel):
    email: str
    username: str
    name: str
    guardian_email: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    interests: Optional[List[str]] = []
    background_tracking_enabled: Optional[bool] = False
    report_frequency: Optional[str] = "daily"
    report_enabled: Optional[bool] = True


class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: str = Field(alias="_id")
    hashed_password: str
    created_at: datetime
    updated_at: datetime
    avatar_url: Optional[str] = None
    theme_preference: str = "dark"
    background_tracking_enabled: bool = False
    report_frequency: str = "daily"
    report_enabled: bool = True
    wellness_score: float = 50.0
    sos_contacts: List[Dict[str, Any]] = []
    
    class Config:
        populate_by_name = True


# Emotion Event Models
class EmotionEventCreate(BaseModel):
    user_id: Optional[str] = None
    emotion: str
    intensity: float
    source: str  # "journal", "face", "chat"
    context: Optional[str] = None
    note: Optional[str] = None  # To support frontend sending "note" instead of "context"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class EmotionEvent(EmotionEventCreate):
    id: str = Field(alias="_id")
    
    class Config:
        populate_by_name = True


# Emotional Tracking Models
class EmotionalWindow(BaseModel):
    user_id: str
    window_start: datetime
    window_end: datetime
    emotions: Dict[str, List[float]]  # emotion -> [intensity values]
    escalation_score: float
    is_critical: bool
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Wellness Score Models
class WellnessScore(BaseModel):
    user_id: str
    date: str
    emotional_wellness_score: float
    stability_score: float
    recovery_index: float
    stress_exposure_score: float
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Journal Entry Models
class JournalEntryCreate(BaseModel):
    content: str
    user_id: Optional[str] = None
    emotions_detected: Optional[List[str]] = None
    mood_intensity: Optional[float] = None
    audio_score: Optional[float] = None
    video_score: Optional[float] = None

    class Config:
        extra = "ignore"


class JournalEntry(JournalEntryCreate):
    id: str = Field(alias="_id")
    created_at: datetime
    emotional_analysis: Dict[str, Any]
    
    class Config:
        populate_by_name = True


# Intervention Models
class InterventionLog(BaseModel):
    user_id: str
    intervention_type: str
    trigger_emotion: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    effectiveness: Optional[float] = None
    user_feedback: Optional[str] = None


# Chatbot Models
class ChatMessage(BaseModel):
    user_id: str
    sender: str  # "user" or "bot"
    message: str
    emotional_context: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Safe Links Models
class SafeLink(BaseModel):
    user_id: str
    title: str
    url: str
    category: str  # "music", "video", "exercise", "meditation"
    created_at: datetime = Field(default_factory=datetime.utcnow)


# SOS System Models
class SOSContact(BaseModel):
    user_id: str
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    type: str  # "emergency", "friend", "family"
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Insight Models
class DailyInsight(BaseModel):
    user_id: str
    date: str
    insights: List[str]
    patterns: List[str]
    recommendations: List[str]
    created_at: datetime = Field(default_factory=datetime.utcnow)
