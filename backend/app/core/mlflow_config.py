"""
Centralized MLflow configuration and helper utilities for MindTrace AI+.

All MLflow operations are gated behind MLFLOW_ENABLED — when disabled, every
helper is a silent no-op so the application runs identically without MLflow.
"""

import logging
import time
import hashlib
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy globals — populated by init_mlflow()
# ---------------------------------------------------------------------------
_mlflow = None          # The mlflow module itself (lazy-imported)
_initialized = False
MLFLOW_ENABLED = False


def init_mlflow():
    """
    Initialize MLflow from application settings.
    Call once during app startup (e.g. in FastAPI lifespan or script entry).
    Safe to call multiple times — subsequent calls are no-ops.
    """
    global _mlflow, _initialized, MLFLOW_ENABLED

    if _initialized:
        return

    try:
        from app.core.config import settings
        MLFLOW_ENABLED = settings.MLFLOW_ENABLED
    except Exception:
        MLFLOW_ENABLED = False

    if not MLFLOW_ENABLED:
        _initialized = True
        logger.info("MLflow tracking is DISABLED (MLFLOW_ENABLED=False)")
        return

    try:
        import mlflow as _mlflow_module
        _mlflow = _mlflow_module

        from app.core.config import settings
        _mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
        _initialized = True
        logger.info(
            f"MLflow initialized — tracking URI: {settings.MLFLOW_TRACKING_URI}"
        )
    except ImportError:
        MLFLOW_ENABLED = False
        _initialized = True
        logger.warning(
            "mlflow package not installed — tracking disabled. "
            "Install with: pip install mlflow>=2.12.0"
        )
    except Exception as exc:
        MLFLOW_ENABLED = False
        _initialized = True
        logger.error(f"MLflow initialization failed: {exc}")


# ---------------------------------------------------------------------------
# Experiment helpers
# ---------------------------------------------------------------------------

def get_or_create_experiment(name: str) -> Optional[str]:
    """Return the experiment ID for *name*, creating it if necessary."""
    if not MLFLOW_ENABLED or _mlflow is None:
        return None
    try:
        from app.core.config import settings
        full_name = f"{settings.MLFLOW_EXPERIMENT_PREFIX}-{name}"
        exp = _mlflow.get_experiment_by_name(full_name)
        if exp is not None:
            return exp.experiment_id
        return _mlflow.create_experiment(full_name)
    except Exception as exc:
        logger.error(f"MLflow get_or_create_experiment error: {exc}")
        return None


def start_run(experiment_name: str, run_name: str = None, nested: bool = False, tags: Dict[str, str] = None):
    """
    Convenience wrapper around mlflow.start_run().
    Returns a context-manager (the run) or a dummy context-manager when disabled.
    """
    if not MLFLOW_ENABLED or _mlflow is None:
        return _DummyRun()

    try:
        exp_id = get_or_create_experiment(experiment_name)
        return _mlflow.start_run(
            experiment_id=exp_id,
            run_name=run_name,
            nested=nested,
            tags=tags,
        )
    except Exception as exc:
        logger.error(f"MLflow start_run error: {exc}")
        return _DummyRun()


class _DummyRun:
    """No-op context manager returned when MLflow is disabled."""
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass


# ---------------------------------------------------------------------------
# Metric / param / artifact logging
# ---------------------------------------------------------------------------

def log_params(params: Dict[str, Any]):
    """Log a dict of parameters to the active run."""
    if not MLFLOW_ENABLED or _mlflow is None:
        return
    try:
        _mlflow.log_params(params)
    except Exception as exc:
        logger.debug(f"MLflow log_params error: {exc}")


def log_metrics(metrics: Dict[str, float], step: int = None):
    """Log a dict of metrics to the active run."""
    if not MLFLOW_ENABLED or _mlflow is None:
        return
    try:
        _mlflow.log_metrics(metrics, step=step)
    except Exception as exc:
        logger.debug(f"MLflow log_metrics error: {exc}")


def log_artifact(local_path: str):
    """Log a local file as an artifact."""
    if not MLFLOW_ENABLED or _mlflow is None:
        return
    try:
        _mlflow.log_artifact(local_path)
    except Exception as exc:
        logger.debug(f"MLflow log_artifact error: {exc}")


def set_tags(tags: Dict[str, str]):
    """Set tags on the active run."""
    if not MLFLOW_ENABLED or _mlflow is None:
        return
    try:
        _mlflow.set_tags(tags)
    except Exception as exc:
        logger.debug(f"MLflow set_tags error: {exc}")


def end_run():
    """End the current active run."""
    if not MLFLOW_ENABLED or _mlflow is None:
        return
    try:
        _mlflow.end_run()
    except Exception as exc:
        logger.debug(f"MLflow end_run error: {exc}")


# ---------------------------------------------------------------------------
# High-level LLM / inference logging helpers
# ---------------------------------------------------------------------------

def log_llm_call(
    service_name: str,
    model_name: str,
    function_name: str,
    prompt: str,
    response_text: str,
    latency_ms: float,
    temperature: float = None,
    max_tokens: int = None,
    extra_params: Dict[str, Any] = None,
):
    """
    Log a single LLM inference call as a nested MLflow run.

    Parameters
    ----------
    service_name : str   — e.g. "gemini", "groq"
    model_name : str     — e.g. "gemini-2.5-flash", "llama-3.3-70b-versatile"
    function_name : str  — the calling method name
    prompt : str         — user/system prompt (hashed for storage efficiency)
    response_text : str  — the LLM response text
    latency_ms : float   — wall-clock latency in milliseconds
    temperature : float  — generation temperature (optional)
    max_tokens : int     — max_tokens setting (optional)
    extra_params : dict  — any additional params to log
    """
    if not MLFLOW_ENABLED or _mlflow is None:
        return

    try:
        exp_id = get_or_create_experiment("LLM-Inference")
        with _mlflow.start_run(experiment_id=exp_id, run_name=f"{service_name}/{function_name}", nested=True):
            params = {
                "service": service_name,
                "model": model_name,
                "function": function_name,
                "prompt_hash": hashlib.md5(prompt.encode()).hexdigest()[:12],
                "prompt_length": len(prompt),
                "response_length": len(response_text) if response_text else 0,
            }
            if temperature is not None:
                params["temperature"] = temperature
            if max_tokens is not None:
                params["max_tokens"] = max_tokens
            if extra_params:
                params.update({k: str(v) for k, v in extra_params.items()})

            _mlflow.log_params(params)
            _mlflow.log_metrics({
                "latency_ms": latency_ms,
                "prompt_chars": len(prompt),
                "response_chars": len(response_text) if response_text else 0,
            })
            _mlflow.set_tags({
                "run_type": "llm_inference",
                "service": service_name,
                "model": model_name,
            })
    except Exception as exc:
        logger.debug(f"MLflow log_llm_call error: {exc}")


def log_hf_inference(
    model_name: str,
    input_text: str,
    result: Dict[str, Any],
    latency_ms: float,
):
    """
    Log a HuggingFace Inference API call as a nested MLflow run.
    """
    if not MLFLOW_ENABLED or _mlflow is None:
        return

    try:
        exp_id = get_or_create_experiment("HF-Inference")
        with _mlflow.start_run(experiment_id=exp_id, run_name=f"hf/{model_name.split('/')[-1]}", nested=True):
            _mlflow.log_params({
                "model": model_name,
                "input_length": len(input_text) if input_text else 0,
            })

            metrics = {"latency_ms": latency_ms}
            dominant = result.get("dominant_emotion") or result.get("dominant")
            intensity = result.get("dominant_intensity") or result.get("intensity")
            if intensity is not None:
                metrics["confidence"] = float(intensity)

            _mlflow.log_metrics(metrics)
            _mlflow.set_tags({
                "run_type": "hf_inference",
                "model": model_name,
                "dominant_emotion": str(dominant) if dominant else "unknown",
            })
    except Exception as exc:
        logger.debug(f"MLflow log_hf_inference error: {exc}")


def log_inference_call(
    experiment_name: str,
    run_name: str,
    params: Dict[str, Any],
    metrics: Dict[str, float],
    tags: Dict[str, str] = None,
):
    """
    Generic inference logging — logs a single inference as a nested run.
    Used for emotion detector pipeline-level tracking.
    """
    if not MLFLOW_ENABLED or _mlflow is None:
        return

    try:
        exp_id = get_or_create_experiment(experiment_name)
        with _mlflow.start_run(experiment_id=exp_id, run_name=run_name, nested=True):
            safe_params = {k: str(v) for k, v in params.items()}
            _mlflow.log_params(safe_params)
            _mlflow.log_metrics(metrics)
            if tags:
                _mlflow.set_tags(tags)
    except Exception as exc:
        logger.debug(f"MLflow log_inference_call error: {exc}")


# ---------------------------------------------------------------------------
# Timer utility
# ---------------------------------------------------------------------------

class Timer:
    """Simple context-manager timer that captures elapsed milliseconds."""
    def __init__(self):
        self.start = None
        self.elapsed_ms = 0.0

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.elapsed_ms = (time.perf_counter() - self.start) * 1000
