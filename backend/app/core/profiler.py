"""
Performance Profiling Middleware for MindTrace-AI+
===================================================
Measures execution time of every request and logs slow endpoints.
Uses a module-level shared stats dict so the API endpoint can access the data.
"""

import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("mindtrace.profiler")

# Module-level shared stats — accessible from both the middleware and the API endpoint
_shared_stats: dict[str, dict] = {}
SLOW_THRESHOLD_MS = 5000


class PerformanceProfilerMiddleware(BaseHTTPMiddleware):
    """
    Lightweight middleware that:
    1. Measures wall-clock time for every request.
    2. Adds X-Process-Time header to every response.
    3. Logs a WARNING for any request exceeding SLOW_THRESHOLD_MS.
    4. Tracks aggregate stats in the module-level _shared_stats dict.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()

        response = await call_next(request)

        elapsed_ms = (time.perf_counter() - start) * 1000
        route = f"{request.method} {request.url.path}"

        # Add timing header
        response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.1f}"

        # Track aggregate stats in the shared dict
        if route not in _shared_stats:
            _shared_stats[route] = {
                "count": 0,
                "total_ms": 0,
                "max_ms": 0,
                "min_ms": float("inf"),
                "slow_count": 0,
            }
        s = _shared_stats[route]
        s["count"] += 1
        s["total_ms"] += elapsed_ms
        s["max_ms"] = max(s["max_ms"], elapsed_ms)
        s["min_ms"] = min(s["min_ms"], elapsed_ms)

        # Log slow requests
        if elapsed_ms > SLOW_THRESHOLD_MS:
            s["slow_count"] += 1
            logger.warning(
                f"SLOW REQUEST: {route} took {elapsed_ms:.0f}ms "
                f"(threshold: {SLOW_THRESHOLD_MS}ms)"
            )

        return response


def get_perf_stats() -> dict:
    """Return formatted performance statistics."""
    result = {}
    for route, s in sorted(_shared_stats.items(), key=lambda x: x[1]["total_ms"], reverse=True):
        avg = s["total_ms"] / s["count"] if s["count"] else 0
        result[route] = {
            "requests": s["count"],
            "avg_ms": round(avg, 1),
            "max_ms": round(s["max_ms"], 1),
            "min_ms": round(s["min_ms"], 1) if s["min_ms"] != float("inf") else 0,
            "slow_requests": s["slow_count"],
            "total_time_s": round(s["total_ms"] / 1000, 2),
        }
    return result


def reset_perf_stats():
    """Clear all tracked statistics."""
    _shared_stats.clear()
