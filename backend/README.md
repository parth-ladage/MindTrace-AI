# MINDTRACE AI+ Backend

Realtime Emotional Intelligence and Adaptive Wellness Platform Backend

## Overview

This is a production-grade FastAPI backend that powers MINDTRACE AI+, providing:

- **Realtime Emotion Detection**: Continuous emotional analysis using transformer models
- **Emotional Tracking Engine**: Core innovation - tracks emotional escalation patterns
- **Adaptive Interventions**: Intelligent recommendation system for wellness activities
- **Analytics & Insights**: Daily wellness scores and emotional trend analysis
- **WebSocket Integration**: Real-time updates and notifications
- **Secure API**: JWT authentication with role-based access
- **Scalable Architecture**: Async/await with MongoDB and Redis

## Technology Stack

- **Framework**: FastAPI with Uvicorn
- **Database**: MongoDB (Atlas or Local)
- **Cache**: Redis
- **AI/ML**: Hugging Face Transformers, Sentence Transformers
- **Async**: AsyncIO, Motor (async MongoDB)
- **Real-time**: WebSockets
- **Auth**: JWT + Passlib

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── auth.py           # Authentication endpoints
│   │   ├── emotions.py       # Emotion detection & tracking
│   │   ├── journal.py        # Journaling engine
│   │   ├── interventions.py  # Intervention system
│   │   ├── analytics.py      # Analytics & insights
│   │   ├── chatbot.py        # Emotional support chatbot
│   │   ├── sos.py            # SOS & safety system
│   │   ├── safe_links.py     # Comfort content management
│   │   └── users.py          # User management
│   ├── ai/
│   │   └── emotion_detector.py   # NLP emotion detection
│   ├── services/
│   │   ├── emotional_tracking.py # Core tracking engine
│   │   ├── scoring_engine.py     # Wellness scoring
│   │   ├── intervention_engine.py # Intervention logic
│   │   └── analytics_engine.py   # Analytics generation
│   ├── websocket/
│   │   └── manager.py        # WebSocket connection management
│   ├── core/
│   │   ├── config.py         # Configuration
│   │   ├── database.py       # MongoDB connection
│   │   └── security.py       # JWT & password hashing
│   └── schemas/
│       └── models.py         # Pydantic models
├── main.py                   # FastAPI app entry point
├── requirements.txt          # Python dependencies


```

## Key Features

### 1. Realtime Emotion Detection
```python
# Detect emotions from text
POST /api/emotions/detect
{
    "text": "I've been feeling really anxious lately..."
}
```

### 2. Emotional Tracking Engine
- Continuous monitoring of emotional events
- Escalation pattern detection
- Weighted emotion scoring
- Recency-based analysis
- Rolling window calculations

### 3. Adaptive Interventions
- Personalized intervention recommendations
- Staged escalation system
- Effectiveness tracking
- Coping strategy suggestions

### 4. Real-time Analytics
- Daily wellness scores
- Emotional trend analysis
- Trigger identification
- Emotional heatmaps
- Recovery index calculation

### 5. WebSocket Real-time Updates
```
ws://localhost:8000/api/emotions/stream/{user_id}

Events:
- emotion_detected
- escalation_detected
- wellness_update
- intervention_triggered
- daily_insights
```

## Setup & Installation



### Manual Setup

1. **Install Python 3.11+**

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up MongoDB**
```bash
# Using MongoDB Atlas
# Create cluster at https://cloud.mongodb.com
# Get connection string and set MONGODB_URL
```

5. **Set up Redis**
```bash
# On Windows: Download from https://github.com/microsoftarchive/redis/releases

```

6. **Create .env file**
```bash
cp .env.example .env
# Edit .env with your settings
```

7. **Run FastAPI server**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### Authentication
- `POST /api/auth/signup` - Register new user
- `POST /api/auth/login` - Login user
- `POST /api/auth/refresh` - Refresh token

### Emotions
- `POST /api/emotions/detect` - Detect emotions from text
- `POST /api/emotions/record` - Record emotion event
- `GET /api/emotions/history` - Get emotion history
- `GET /api/emotions/status` - Get current emotional status
- `WS /api/emotions/stream/{user_id}` - Real-time stream

### Journaling
- `POST /api/journal/create` - Create journal entry
- `GET /api/journal/list` - List entries
- `GET /api/journal/{entry_id}` - Get specific entry
- `DELETE /api/journal/{entry_id}` - Delete entry

### Interventions
- `GET /api/interventions/recommend` - Get recommendations
- `GET /api/interventions/sequence` - Get intervention workflow
- `POST /api/interventions/trigger/{type}` - Trigger intervention
- `POST /api/interventions/feedback/{log_id}` - Submit feedback

### Analytics
- `GET /api/analytics/daily-score` - Daily wellness score
- `GET /api/analytics/insights` - Daily insights
- `GET /api/analytics/triggers` - Emotional triggers
- `GET /api/analytics/dashboard` - Complete dashboard

### Chatbot
- `POST /api/chatbot/send-message` - Send message
- `GET /api/chatbot/conversation-history` - Get history
- `GET /api/chatbot/emotional-support-tips` - Get tips

### Safe Links
- `POST /api/safe-links/add` - Add comfort content link
- `GET /api/safe-links/list` - List links
- `POST /api/safe-links/{link_id}/access` - Track access

### SOS & Safety
- `POST /api/sos/contact/add` - Add emergency contact
- `GET /api/sos/contact/list` - List contacts
- `POST /api/sos/alert` - Send SOS alert

### Users
- `GET /api/users/profile` - Get user profile
- `PUT /api/users/profile` - Update profile
- `GET /api/users/wellness-stats` - Get wellness stats
- `GET /api/users/activity-summary` - Activity summary

## Database Collections

- `users` - User accounts and profiles
- `realtime_emotion_events` - Emotion tracking events
- `wellness_scores` - Daily wellness metrics
- `journal_entries` - Journal entries with emotion analysis
- `intervention_logs` - Intervention usage and effectiveness
- `recovery_sessions` - Recovery activity sessions
- `daily_insights` - Daily generated insights
- `chatbot_messages` - Chatbot conversation history
- `sos_contacts` - Emergency contacts
- `user_safe_links` - Comfort content collection
- `sos_alerts` - SOS alert history

## Development

### Running Tests
```bash
pytest tests/
```

### Code Style
```bash
# Format code
black app/

# Lint code
flake8 app/

# Type checking
mypy app/
```

### Database Migrations
```bash
# MongoDB uses schema-on-read, but for major changes:
# Edit models in schemas/models.py
# Run migrations manually or through admin panel
```

## Deployment

### Deploy to Render

1. Push code to GitHub
2. Create new Web Service on Render
3. Set environment variables:
   - `MONGODB_URL` - MongoDB Atlas connection string
   - `REDIS_URL` - Redis connection string
   - `SECRET_KEY` - Generate a secure key
   - `DEBUG` - Set to False

4. Set build command: `pip install -r requirements.txt`
5. Set start command: `uvicorn main:app --host 0.0.0.0`

### Deploy to Railway

1. Connect GitHub repository
2. Railway auto-detects Python
3. Add MongoDB and Redis plugins
4. Set environment variables
5. Deploy

### Deploy to DigitalOcean App Platform

1. Connect GitHub
2. Create app.yaml:
```yaml
services:
  - http:
      routes:
        - path: /
      source:
            branch: main
            repo: your-repo
```

## Performance Optimization

1. **Caching**: Redis for frequently accessed data
2. **Async Processing**: All database operations are async
3. **Model Optimization**: Using distilled BERT models
4. **Batch Processing**: Emotion analysis batching
5. **Connection Pooling**: MongoDB connection pooling

## Security

- JWT token-based authentication
- Password hashing with bcrypt
- CORS configuration
- Input validation with Pydantic
- SQL injection protection (using MongoDB driver)
- Rate limiting recommended (implement with FastAPI-Limiter)

## Monitoring & Logging

```python
import logging

logger = logging.getLogger(__name__)

# Logs are written to stdout
# Monitor via:
# - CloudWatch (AWS)
# - Datadog
# - ELK Stack
# - Application Insights (Azure)
```

## Troubleshooting

### MongoDB Connection Error
```bash
# Check connection string
# Ensure IP whitelist on MongoDB Atlas includes your server
# Verify credentials
```

### Model Loading Errors
```bash
# First run will download ~1GB of models
# Ensure adequate disk space
# Models are cached in ~/.cache/huggingface
```

### WebSocket Connection Issues
```bash
# Ensure CORS is configured correctly
# Check firewall for port 8000
# WebSocket proxy support in nginx
```

## Contributing

1. Create feature branch
2. Make changes following code style
3. Add tests
4. Create pull request

## License

MIT License - MINDTRACE AI+

## Support

For issues and questions:
- Open GitHub issue
- Email: support@mindtrace.ai
- Documentation: https://docs.mindtrace.ai
