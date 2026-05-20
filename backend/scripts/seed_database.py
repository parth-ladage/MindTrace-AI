"""
MindTrace-AI+ Mass Data Seeding Script
=======================================
Generates 50 synthetic users with 90 days of realistic emotional data.
Run with:  python -m scripts.seed_database
"""

import asyncio
import random
import hashlib
import sys
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add backend root to sys.path so we can import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import motor.motor_asyncio
from dotenv import load_dotenv

load_dotenv()

# ─── Configuration ───────────────────────────────────────────────
NUM_USERS = 50
DAYS_OF_HISTORY = 90
MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017/mindtrace")
MONGODB_DB = os.getenv("MONGODB_DB", "mindtrace_db")
DEFAULT_PASSWORD_HASH = None  # Will be set in main()

# ─── Seed Data Pools ────────────────────────────────────────────
FIRST_NAMES = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun",
    "Ananya", "Diya", "Priya", "Isha", "Meera",
    "Rohan", "Karan", "Neha", "Pooja", "Rahul",
    "Sneha", "Amit", "Riya", "Sanjay", "Kavya",
    "Liam", "Emma", "Noah", "Olivia", "Ethan",
    "Sophia", "Mason", "Isabella", "Lucas", "Mia",
    "Akira", "Yuki", "Hana", "Ryu", "Sakura",
    "Chen", "Wei", "Xin", "Mei", "Jun",
    "Omar", "Fatima", "Ali", "Zara", "Hassan",
    "Grace", "Felix", "Luna", "Leo", "Maya"
]

OCCUPATIONS = [
    "Student", "Software Engineer", "Teacher", "Designer", "Doctor",
    "Artist", "Freelancer", "Manager", "Writer", "Researcher",
    "Nurse", "Entrepreneur", "Therapist", "Chef", "Musician"
]

INTERESTS_POOL = [
    "meditation", "yoga", "reading", "gaming", "cooking",
    "music", "painting", "hiking", "photography", "journaling",
    "fitness", "travel", "coding", "gardening", "dancing"
]

GENDERS = ["male", "female", "non-binary", "prefer not to say"]

EMOTIONS = ["joy", "neutral", "sadness", "anger", "fear", "surprise", "disgust"]
NEGATIVE_EMOTIONS = ["sadness", "anger", "fear", "disgust"]
POSITIVE_EMOTIONS = ["joy", "surprise"]

# Realistic journal templates organized by mood category
JOURNAL_TEMPLATES = {
    "positive": [
        "Had an amazing day today! Everything just clicked — I finished my tasks ahead of schedule and had time to relax in the evening.",
        "Feeling grateful for the little things. The weather was perfect, I had a great conversation with a friend, and dinner was delicious.",
        "I'm really proud of myself today. I finally tackled that project I've been putting off and it turned out great!",
        "Started the morning with meditation and it set the tone for the whole day. I felt calm, focused, and productive.",
        "Something wonderful happened — I got positive feedback on my work! It really boosted my confidence.",
        "Today was full of laughter. Spent quality time with people I care about and it reminded me how important connections are.",
        "Woke up feeling energized and motivated. Went for a run, cooked a healthy breakfast, and crushed my to-do list.",
        "A beautiful sunset today made me pause and appreciate the moment. Sometimes the simplest things bring the most joy.",
    ],
    "neutral": [
        "A fairly routine day. Nothing extraordinary happened but nothing bad either. Just went through the motions.",
        "Spent most of the day working. It wasn't particularly exciting but I got things done, which is what matters.",
        "Mixed bag today — some things went well, others not so much. Overall, I'm feeling okay about where I stand.",
        "Had a quiet day at home. Did some chores, watched a show, and called my parents. It was simple but nice.",
        "Today was average. I'm not feeling particularly up or down, just kind of coasting through the week.",
        "Attended a couple of meetings and ran some errands. The day went by fast without any major highlights.",
    ],
    "negative": [
        "Feeling really overwhelmed today. Work pressure is mounting and I can't seem to catch a break. I need to find better coping strategies.",
        "Had a disagreement with someone close to me and it's weighing on my mind. I keep replaying the conversation in my head.",
        "I'm exhausted — physically and mentally. Haven't been sleeping well and it's starting to affect everything else.",
        "Struggling with self-doubt today. I feel like I'm falling behind while everyone else is moving forward.",
        "Anxiety has been really high lately. I keep worrying about things that haven't even happened yet. Need to ground myself.",
        "Feeling isolated and lonely. Haven't really connected with anyone meaningful in a while and it's getting to me.",
        "A tough day at work. Made a mistake that felt really embarrassing and I can't shake the feeling of frustration.",
        "Couldn't focus at all today. My mind kept wandering to negative thoughts and I couldn't pull myself out of it.",
    ],
    "critical": [
        "I feel completely lost and don't know what to do anymore. Everything feels pointless and I'm struggling to see a way forward.",
        "The weight of everything is crushing me. I don't feel like getting out of bed and facing another day like this.",
        "I feel so alone in this. Nobody understands what I'm going through and I don't know how to ask for help.",
    ]
}


def _generate_mood_arc(days: int) -> list[str]:
    """
    Generate a realistic mood arc for a user over N days.
    Simulates: weekday stress, weekend relief, and a gradual overall arc.
    Returns a list of mood categories per day: 'positive', 'neutral', 'negative', 'critical'
    """
    arc_type = random.choice(["improving", "declining", "stable", "volatile"])
    moods = []

    for day_index in range(days):
        day_of_week = (datetime.now(timezone.utc) - timedelta(days=days - 1 - day_index)).weekday()
        is_weekend = day_of_week >= 5

        # Base probability distribution
        if arc_type == "improving":
            progress = day_index / days
            p_pos = 0.2 + 0.5 * progress
            p_neg = 0.4 - 0.35 * progress
            p_crit = max(0, 0.05 - 0.04 * progress)
        elif arc_type == "declining":
            progress = day_index / days
            p_pos = 0.5 - 0.4 * progress
            p_neg = 0.2 + 0.4 * progress
            p_crit = 0.01 + 0.06 * progress
        elif arc_type == "volatile":
            # Random swings
            swing = random.random()
            p_pos = 0.4 * swing
            p_neg = 0.4 * (1 - swing)
            p_crit = 0.03
        else:  # stable
            p_pos = 0.35
            p_neg = 0.2
            p_crit = 0.02

        # Weekend boost
        if is_weekend:
            p_pos += 0.15
            p_neg -= 0.1

        p_neutral = max(0, 1.0 - p_pos - p_neg - p_crit)

        mood = random.choices(
            ["positive", "neutral", "negative", "critical"],
            weights=[p_pos, p_neutral, p_neg, p_crit],
            k=1
        )[0]
        moods.append(mood)

    return moods


def _emotion_for_mood(mood: str) -> tuple[str, float]:
    """Return an (emotion, intensity) pair that matches the mood category."""
    if mood == "positive":
        emotion = random.choice(POSITIVE_EMOTIONS)
        intensity = random.uniform(0.6, 0.95)
    elif mood == "negative":
        emotion = random.choice(NEGATIVE_EMOTIONS)
        intensity = random.uniform(0.5, 0.8)
    elif mood == "critical":
        emotion = random.choice(["sadness", "fear"])
        intensity = random.uniform(0.85, 0.98)
    else:
        emotion = "neutral"
        intensity = random.uniform(0.3, 0.6)
    return emotion, intensity


def _positivity_for_mood(mood: str, intensity: float) -> float:
    """Calculate a positivity score based on mood and intensity."""
    if mood in ("negative", "critical"):
        return round(max(0.05, 1.0 - intensity - random.uniform(0, 0.15)), 3)
    elif mood == "positive":
        return round(min(0.98, intensity + random.uniform(0, 0.1)), 3)
    else:
        return round(0.4 + random.uniform(0, 0.2), 3)


async def seed_users(db) -> list[dict]:
    """Create 50 synthetic users and return their records."""
    import bcrypt

    users = []
    # Pre-hash one password for all users (fast)
    password_bytes = "Test@1234".encode("utf-8")
    shared_hash = bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")

    print(f"  Creating {NUM_USERS} users...", flush=True)

    for i in range(NUM_USERS):
        name = FIRST_NAMES[i % len(FIRST_NAMES)]
        email = f"{name.lower()}.test{i+1}@mindtrace.dev"
        username = f"{name.lower()}_{i+1}"

        user_doc = {
            "email": email,
            "username": username,
            "name": name,
            "hashed_password": shared_hash,
            "created_at": datetime.now(timezone.utc) - timedelta(days=DAYS_OF_HISTORY + random.randint(0, 30)),
            "updated_at": datetime.now(timezone.utc),
            "theme_preference": random.choice(["dark", "light"]),
            "wellness_score": round(random.uniform(30, 85), 1),
            "avatar_url": None,
            "guardian_email": f"guardian.{name.lower()}@example.com" if random.random() > 0.5 else None,
            "age": random.randint(14, 55),
            "gender": random.choice(GENDERS),
            "occupation": random.choice(OCCUPATIONS),
            "bio": f"Hi, I'm {name}. Just tracking my mental wellness journey.",
            "interests": random.sample(INTERESTS_POOL, k=random.randint(2, 5)),
            "background_tracking_enabled": random.choice([True, False]),
            "report_frequency": random.choice(["daily", "weekly"]),
            "report_enabled": True,
            "is_seed": True  # Tag so we can clean up later
        }

        result = await db.users.insert_one(user_doc)
        user_doc["_id"] = result.inserted_id
        users.append(user_doc)

    print(f"  [OK] Created {len(users)} users", flush=True)
    return users


async def seed_data_for_user(db, user: dict, user_index: int):
    """Generate 90 days of journals + emotion events for a single user."""
    user_id = str(user["_id"])
    mood_arc = _generate_mood_arc(DAYS_OF_HISTORY)

    journal_docs = []
    emotion_docs = []
    wellness_docs = []

    for day_offset, mood in enumerate(mood_arc):
        target_date = datetime.now(timezone.utc) - timedelta(days=DAYS_OF_HISTORY - 1 - day_offset)

        # --- Skip some days randomly (realistic gaps) -------------
        if random.random() < 0.12:  # ~12% chance of no entry
            continue

        # --- Journal Entry ----------------------------------------
        templates = JOURNAL_TEMPLATES.get(mood, JOURNAL_TEMPLATES["neutral"])
        content = random.choice(templates)
        emotion, intensity = _emotion_for_mood(mood)
        positivity = _positivity_for_mood(mood, intensity)

        journal_doc = {
            "user_id": user_id,
            "content": content,
            "emotions_detected": [emotion],
            "all_scores": {e: round(random.uniform(0.01, 0.15), 3) for e in EMOTIONS},
            "dominant_emotion": emotion,
            "dominant_intensity": round(intensity, 3),
            "text_score": round(positivity, 3),
            "audio_score": round(positivity + random.uniform(-0.1, 0.1), 3),
            "video_score": round(positivity + random.uniform(-0.1, 0.1), 3),
            "positivity": positivity,
            "mood_intensity": round(intensity, 3),
            "sentiment": mood,
            "suggestions": [],
            "created_at": target_date.replace(
                hour=random.randint(7, 23),
                minute=random.randint(0, 59)
            ),
            "updated_at": target_date,
            "is_seed": True
        }
        # Overwrite the dominant emotion's score to be dominant
        journal_doc["all_scores"][emotion] = round(intensity, 3)
        journal_docs.append(journal_doc)

        # --- Emotion Events (2-6 per day from sensors) ------------
        num_events = random.randint(2, 6)
        for _ in range(num_events):
            ev_emotion, ev_intensity = _emotion_for_mood(
                random.choices([mood, "neutral"], weights=[0.7, 0.3], k=1)[0]
            )
            event_doc = {
                "user_id": user_id,
                "emotion": ev_emotion,
                "intensity": round(ev_intensity, 3),
                "source": random.choice(["sensor", "face_detection", "journal", "chat"]),
                "timestamp": target_date.replace(
                    hour=random.randint(6, 23),
                    minute=random.randint(0, 59),
                    second=random.randint(0, 59)
                ),
                "is_seed": True
            }
            emotion_docs.append(event_doc)

        # --- Daily Wellness Score ---------------------------------
        if mood == "positive":
            ew = random.uniform(65, 95)
        elif mood == "negative":
            ew = random.uniform(25, 50)
        elif mood == "critical":
            ew = random.uniform(10, 30)
        else:
            ew = random.uniform(45, 70)

        wellness_doc = {
            "user_id": user_id,
            "date": target_date.strftime("%Y-%m-%d"),
            "emotional_wellness_score": round(ew, 1),
            "stability_score": round(random.uniform(0.3, 0.9), 2),
            "recovery_index": round(random.uniform(0.2, 0.95), 2),
            "stress_exposure_score": round(1.0 - (ew / 100), 2),
            "created_at": target_date,
            "is_seed": True
        }
        wellness_docs.append(wellness_doc)

    # --- Bulk Insert ----------------------------------------------
    if journal_docs:
        await db.journal_entries.insert_many(journal_docs)
    if emotion_docs:
        await db.realtime_emotion_events.insert_many(emotion_docs)
    if wellness_docs:
        await db.wellness_scores.insert_many(wellness_docs)

    return len(journal_docs), len(emotion_docs), len(wellness_docs)


async def main():
    print("=" * 60)
    print("  MindTrace-AI+ Data Seeding Script")
    print(f"  Target: {NUM_USERS} users x {DAYS_OF_HISTORY} days")
    print(f"  Database: {MONGODB_DB}")
    print("=" * 60)

    client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
    db = client[MONGODB_DB]

    # --- Optional: Clean old seed data -----------------------------
    print("\n[1/3] Cleaning previous seed data...")
    del_users = await db.users.delete_many({"is_seed": True})
    del_journals = await db.journal_entries.delete_many({"is_seed": True})
    del_events = await db.realtime_emotion_events.delete_many({"is_seed": True})
    del_wellness = await db.wellness_scores.delete_many({"is_seed": True})
    print(f"  Cleaned: {del_users.deleted_count} users, {del_journals.deleted_count} journals, "
          f"{del_events.deleted_count} events, {del_wellness.deleted_count} wellness scores")

    # --- Create Users ----------------------------------------------
    print("\n[2/3] Seeding users...")
    users = await seed_users(db)

    # --- Generate History ------------------------------------------
    print(f"\n[3/3] Generating {DAYS_OF_HISTORY}-day history per user...")
    total_journals = 0
    total_events = 0
    total_wellness = 0

    for idx, user in enumerate(users):
        j, e, w = await seed_data_for_user(db, user, idx)
        total_journals += j
        total_events += e
        total_wellness += w

        if (idx + 1) % 10 == 0 or idx == len(users) - 1:
            print(f"  Progress: {idx + 1}/{len(users)} users seeded", flush=True)

    # --- Summary --------------------------------------------------
    print("\n" + "=" * 60)
    print("  [OK] SEEDING COMPLETE")
    print("=" * 60)
    print(f"  Users created:        {len(users)}")
    print(f"  Journal entries:      {total_journals:,}")
    print(f"  Emotion events:       {total_events:,}")
    print(f"  Wellness scores:      {total_wellness:,}")
    print(f"  Total documents:      {total_journals + total_events + total_wellness:,}")
    print()
    print("  Login credentials for any seeded user:")
    print(f"     Email:    {users[0]['email']}")
    print(f"     Password: Test@1234")
    print("=" * 60)

    client.close()


if __name__ == "__main__":
    asyncio.run(main())
