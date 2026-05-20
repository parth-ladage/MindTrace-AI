"""
MindTrace-AI+ Load Test (Locust)
=================================
Simulates realistic user behavior flows against the API.

Run with:
  locust -f locustfile.py --host http://localhost:8000

Or headless (100 users, 10/sec ramp, 2 min):
  locust -f locustfile.py --host http://localhost:8000 --headless -u 100 -r 10 --run-time 2m
"""

from locust import HttpUser, task, between, events
import random
import json
import logging

logger = logging.getLogger(__name__)

# Pre-generated test accounts (created by seed_database.py)
# All share password "Test@1234"
TEST_EMAILS = [f"{name.lower()}.test{i+1}@mindtrace.dev" for i, name in enumerate([
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
])]

SAMPLE_JOURNAL_ENTRIES = [
    "Today was a good day overall. I managed to get a lot of work done and felt productive throughout.",
    "Feeling a bit stressed about upcoming deadlines but trying to stay positive and focused.",
    "Had a wonderful conversation with an old friend. It really lifted my spirits.",
    "Didn't sleep well last night and it affected my mood all day. Need to work on my sleep habits.",
    "Tried a new meditation technique and it really helped calm my anxiety.",
    "The weather was beautiful today which put me in a great mood for the entire afternoon.",
    "Feeling overwhelmed with responsibilities. Need to prioritize and take things one step at a time.",
    "Had a creative breakthrough on a project I've been working on. Feeling inspired!",
]


class MindTraceUser(HttpUser):
    """
    Simulates a realistic MindTrace user session.
    Each user logs in once, then performs a mix of read-heavy and write operations.
    """
    wait_time = between(1, 5)  # 1-5 seconds between tasks

    def on_start(self):
        """Login and store the access token."""
        self.token = None
        self.user_id = None
        email = random.choice(TEST_EMAILS)

        with self.client.post(
            "/api/auth/login",
            json={"email": email, "password": "Test@1234"},
            catch_response=True,
            name="/api/auth/login"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                self.user_id = data.get("user_id")
                response.success()
            elif response.status_code == 429:
                # Rate limited — this is expected under load
                response.success()
                self.token = None
            else:
                response.failure(f"Login failed: {response.status_code}")

    def _headers(self):
        """Return auth headers or empty dict if not logged in."""
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    # ─── READ-HEAVY TASKS (70% of traffic) ───────────────────────

    @task(10)
    def get_analytics_summary(self):
        """Fetch dashboard analytics summary — most common API call."""
        if not self.token:
            return
        self.client.get(
            "/api/analytics/summary?days=30",
            headers=self._headers(),
            name="/api/analytics/summary"
        )

    @task(8)
    def get_journal_list(self):
        """Paginate through journal entries."""
        if not self.token:
            return
        skip = random.choice([0, 10, 20, 40])
        self.client.get(
            f"/api/journal/list?limit=20&skip={skip}",
            headers=self._headers(),
            name="/api/journal/list"
        )

    @task(6)
    def get_emotion_history(self):
        """Fetch real-time emotion history."""
        if not self.token:
            return
        hours = random.choice([24, 48, 168])
        self.client.get(
            f"/api/emotions/history?hours={hours}",
            headers=self._headers(),
            name="/api/emotions/history"
        )

    @task(5)
    def get_weekly_summary(self):
        """Fetch weekly analytics summary."""
        if not self.token:
            return
        self.client.get(
            "/api/analytics/weekly-summary",
            headers=self._headers(),
            name="/api/analytics/weekly-summary"
        )

    @task(4)
    def get_user_profile(self):
        """Fetch user profile."""
        if not self.token:
            return
        self.client.get(
            "/api/users/profile",
            headers=self._headers(),
            name="/api/users/profile"
        )

    @task(3)
    def get_wellness_score(self):
        """Fetch wellness dashboard data."""
        if not self.token:
            return
        self.client.get(
            "/api/users/wellness",
            headers=self._headers(),
            name="/api/users/wellness"
        )

    # ─── WRITE TASKS (30% of traffic) ────────────────────────────

    @task(3)
    def record_emotion_event(self):
        """Submit a real-time emotion event (simulating face detection)."""
        if not self.token:
            return
        emotions = ["joy", "neutral", "sadness", "anger", "fear", "surprise"]
        self.client.post(
            "/api/emotions/record",
            json={
                "emotion": random.choice(emotions),
                "intensity": round(random.uniform(0.3, 0.9), 2),
                "source": "face_detection",
                "context": "Load test sensor event"
            },
            headers=self._headers(),
            name="/api/emotions/record"
        )

    @task(1)
    def create_journal_entry(self):
        """Submit a journal entry (heaviest write — triggers AI analysis)."""
        if not self.token:
            return
        self.client.post(
            "/api/journal/create",
            json={
                "content": random.choice(SAMPLE_JOURNAL_ENTRIES)
            },
            headers=self._headers(),
            name="/api/journal/create"
        )

    # ─── HEALTH CHECK (lightweight) ──────────────────────────────

    @task(2)
    def health_check(self):
        """Simple health check — tests basic server responsiveness."""
        self.client.get("/health", name="/health")


class HeavyReaderUser(HttpUser):
    """
    Simulates a user who primarily reads data — browsing history and analytics.
    This stresses the read path and database query performance.
    """
    wait_time = between(2, 8)
    weight = 3  # 3x less common than the main user type

    def on_start(self):
        self.token = None
        email = random.choice(TEST_EMAILS)

        with self.client.post(
            "/api/auth/login",
            json={"email": email, "password": "Test@1234"},
            catch_response=True,
            name="/api/auth/login"
        ) as response:
            if response.status_code == 200:
                data = response.json()
                self.token = data.get("access_token")
                response.success()
            elif response.status_code == 429:
                response.success()
            else:
                response.failure(f"Login failed: {response.status_code}")

    def _headers(self):
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}

    @task(5)
    def paginate_journals(self):
        """Aggressively paginate through journal history."""
        if not self.token:
            return
        for page in range(0, 100, 20):
            self.client.get(
                f"/api/journal/list?limit=20&skip={page}",
                headers=self._headers(),
                name="/api/journal/list [paginated]"
            )

    @task(3)
    def fetch_all_analytics(self):
        """Fetch analytics with different time ranges."""
        if not self.token:
            return
        for days in [7, 30, 90]:
            self.client.get(
                f"/api/analytics/summary?days={days}",
                headers=self._headers(),
                name=f"/api/analytics/summary?days={days}"
            )

    @task(2)
    def fetch_long_emotion_history(self):
        """Fetch 7-day emotion history — largest read query."""
        if not self.token:
            return
        self.client.get(
            "/api/emotions/history?hours=168",
            headers=self._headers(),
            name="/api/emotions/history [7d]"
        )
