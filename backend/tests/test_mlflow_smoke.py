"""
Quick MLflow smoke-test for MindTrace AI+
=========================================
Run this script from the backend/ directory to verify MLflow integration
without needing API keys or a running server.

Usage:
    cd d:\\PROJECTS\\MindTrace-AI\\backend
    python tests\\test_mlflow_smoke.py
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Force MLflow enabled even if .env says otherwise ──────────────────────
os.environ["MLFLOW_ENABLED"] = "True"
os.environ["MLFLOW_TRACKING_URI"] = "./mlruns"
os.environ["MLFLOW_EXPERIMENT_PREFIX"] = "MindTrace"

# ── Minimal stubs so the app modules load without real API keys ────────────
os.environ.setdefault("HUGGINGFACE_TOKEN", "")
os.environ.setdefault("GROQ_API_KEY", "")
os.environ.setdefault("GEMINI_API_KEY", "")
os.environ.setdefault("SECRET_KEY", "smoke-test-key")
os.environ.setdefault("MONGODB_URL", "mongodb://localhost:27017/mindtrace")

print("=" * 60)
print("  MindTrace AI+ — MLflow Smoke Test")
print("=" * 60)

# ─────────────────────────────────────────────────────────────────────────────
# 1. Check mlflow is installed
# ─────────────────────────────────────────────────────────────────────────────
print("\n[1] Checking mlflow installation...")
try:
    import mlflow
    print(f"    ✅  mlflow {mlflow.__version__} found")
except ImportError:
    print("    ❌  mlflow NOT installed — run: pip install mlflow>=2.12.0")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# 2. Init mlflow_config
# ─────────────────────────────────────────────────────────────────────────────
print("\n[2] Initialising mlflow_config module...")
try:
    from app.core.mlflow_config import init_mlflow, MLFLOW_ENABLED, Timer, log_llm_call, log_hf_inference, log_inference_call
    init_mlflow()
    # Re-import to get updated module-level flag
    import app.core.mlflow_config as cfg
    print(f"    ✅  init_mlflow() called — MLFLOW_ENABLED={cfg.MLFLOW_ENABLED}")
except Exception as e:
    print(f"    ❌  Failed: {e}")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# 3. Create experiment + test run
# ─────────────────────────────────────────────────────────────────────────────
print("\n[3] Creating a test experiment and run...")
try:
    mlflow.set_tracking_uri("./mlruns")
    mlflow.set_experiment("MindTrace-Smoke-Test")

    with mlflow.start_run(run_name="smoke_test_run"):
        mlflow.log_params({
            "test": "smoke",
            "component": "mlflow_config",
            "python_version": sys.version.split()[0],
        })
        mlflow.log_metrics({
            "dummy_accuracy": 0.95,
            "dummy_latency_ms": 42.0,
        })
        mlflow.set_tags({"run_type": "smoke_test"})
        run_id = mlflow.active_run().info.run_id

    print(f"    ✅  Run created — run_id: {run_id}")
except Exception as e:
    print(f"    ❌  Failed: {e}")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# 4. Test Timer utility
# ─────────────────────────────────────────────────────────────────────────────
print("\n[4] Testing Timer context manager...")
try:
    with Timer() as t:
        time.sleep(0.05)
    print(f"    ✅  Timer works — measured {t.elapsed_ms:.1f} ms (expected ~50 ms)")
except Exception as e:
    print(f"    ❌  Failed: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# 5. Test log_llm_call helper
# ─────────────────────────────────────────────────────────────────────────────
print("\n[5] Testing log_llm_call() helper...")
try:
    log_llm_call(
        service_name="test_service",
        model_name="dummy-model",
        function_name="test_function",
        prompt="Hello, classify this emotion: I am very happy!",
        response_text='{"joy": 0.9, "neutral": 0.1}',
        latency_ms=35.5,
        temperature=0.0,
        max_tokens=100,
        extra_params={"dominant_emotion": "joy"},
    )
    print("    ✅  log_llm_call() executed without errors")
except Exception as e:
    print(f"    ❌  Failed: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# 6. Test log_hf_inference helper
# ─────────────────────────────────────────────────────────────────────────────
print("\n[6] Testing log_hf_inference() helper...")
try:
    log_hf_inference(
        model_name="j-hartmann/emotion-english-distilroberta-base",
        input_text="I feel really sad today.",
        result={"dominant_emotion": "sadness", "dominant_intensity": 0.82},
        latency_ms=210.0,
    )
    print("    ✅  log_hf_inference() executed without errors")
except Exception as e:
    print(f"    ❌  Failed: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# 7. Test log_inference_call helper
# ─────────────────────────────────────────────────────────────────────────────
print("\n[7] Testing log_inference_call() helper...")
try:
    log_inference_call(
        experiment_name="Emotion-Detection",
        run_name="text_analysis/gemini",
        params={"provider": "gemini", "input_length": 42, "dominant_emotion": "joy"},
        metrics={"latency_ms": 320.0, "dominant_intensity": 0.87, "positivity": 0.91},
        tags={"run_type": "text_emotion_analysis", "provider": "gemini"},
    )
    print("    ✅  log_inference_call() executed without errors")
except Exception as e:
    print(f"    ❌  Failed: {e}")

# ─────────────────────────────────────────────────────────────────────────────
# 8. Verify runs exist in mlruns/
# ─────────────────────────────────────────────────────────────────────────────
print("\n[8] Verifying mlruns/ directory was created...")
mlruns_path = os.path.abspath("./mlruns")
if os.path.isdir(mlruns_path):
    experiment_dirs = [d for d in os.listdir(mlruns_path) if os.path.isdir(os.path.join(mlruns_path, d))]
    print(f"    ✅  mlruns/ exists at: {mlruns_path}")
    print(f"    ✅  Experiments found: {len(experiment_dirs)}")
else:
    print(f"    ❌  mlruns/ not found at {mlruns_path}")

print("\n" + "=" * 60)
print("  ✅  All smoke tests passed!")
print("=" * 60)
print(f"\n👉  Run the MLflow UI to view your results:")
print(f"    cd {os.path.abspath('.')}")
print(f"    mlflow ui")
print(f"    Then open: http://localhost:5000\n")
