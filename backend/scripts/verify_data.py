"""Quick verification script to test seeded data and profiler."""
import requests
import json

BASE = "http://localhost:8000"

# Login as seeded user
r = requests.post(f"{BASE}/api/auth/login", json={
    "email": "aarav.test1@mindtrace.dev",
    "password": "Test@1234"
})
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# Fetch analytics
analytics = requests.get(f"{BASE}/api/analytics/summary?days=30", headers=headers)
a = analytics.json()
print("=== ANALYTICS SUMMARY (30 days) ===")
print(f"  Wellness Trend Points: {len(a.get('wellness_trend', []))}")
ed = a.get("emotion_distribution", {})
print(f"  Emotion Distribution: {json.dumps(ed)[:200]}")
print(f"  Total Entries: {a.get('total_entries', 0)}")

# Fetch journals
journals = requests.get(f"{BASE}/api/journal/list?limit=5", headers=headers)
j = journals.json()
print(f"\n=== JOURNAL LIST ===")
print(f"  Total journals: {j.get('total', 0)}")
for entry in j.get("entries", [])[:3]:
    em = entry.get("dominant_emotion", "?")
    content = entry.get("content", "")[:60]
    print(f"  [{em}] {content}...")

# Fetch emotion history
emotions = requests.get(f"{BASE}/api/emotions/history?hours=168", headers=headers)
e = emotions.json()
print(f"\n=== EMOTION HISTORY (7 days) ===")
print(f"  Events returned: {e.get('count', 0)}")

# Check perf stats
perf = requests.get(f"{BASE}/api/perf/stats")
p = perf.json()
print(f"\n=== PERFORMANCE STATS ===")
print(f"  Slow threshold: {p.get('slow_threshold_ms', 0)}ms")
for route, stats in list(p.get("stats", {}).items())[:10]:
    print(f"  {route}: avg={stats['avg_ms']}ms, max={stats['max_ms']}ms, reqs={stats['requests']}, slow={stats['slow_requests']}")
