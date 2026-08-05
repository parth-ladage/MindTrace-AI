import asyncio
import csv
import json
import os
import sys
from collections import defaultdict


# Add backend package to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load backend/.env into environment before importing app modules so pydantic
# Settings (which read env vars) see API keys at import time.
env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if os.path.exists(env_file):
    with open(env_file, 'r', encoding='utf-8') as ef:
        for line in ef:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            k = k.strip()
            v = v.strip()
            if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                v = v[1:-1]
            # Do not print or log secrets
            os.environ.setdefault(k, v)

from app.ai.emotion_detector import emotion_engine

# ==========================================
# MLflow Integration
# ==========================================
try:
    import mlflow
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    print("WARNING: mlflow not installed. Evaluation will proceed without experiment tracking.")


async def analyze_text(text: str):
    result = await emotion_engine.analyze_text_comprehensive(text)
    # prefer returned dominant_emotion if available
    dominant = result.get("dominant_emotion") or None
    emotions = result.get("emotions") or {}
    if not dominant and emotions:
        dominant = max(emotions, key=emotions.get)
    if dominant:
        dominant = dominant.lower()
    return dominant, emotions


def compute_metrics(golds, preds, labels):
    n = len(golds)
    accuracy = sum(1 for g, p in zip(golds, preds) if g == p) / max(1, n)

    label_set = labels
    stats = {}
    for lab in label_set:
        tp = sum(1 for g, p in zip(golds, preds) if g == lab and p == lab)
        fp = sum(1 for g, p in zip(golds, preds) if g != lab and p == lab)
        fn = sum(1 for g, p in zip(golds, preds) if g == lab and p != lab)
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        stats[lab] = {
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
            "support": sum(1 for g in golds if g == lab)
        }

    macro_f1 = round(sum(s["f1"] for s in stats.values()) / max(1, len(stats)), 3)

    # confusion matrix
    idx = {l: i for i, l in enumerate(label_set)}
    cm = [[0 for _ in label_set] for _ in label_set]
    for g, p in zip(golds, preds):
        gi = idx[g]
        pi = idx[p]
        cm[gi][pi] += 1

    return {
        "accuracy": round(accuracy, 3),
        "macro_f1": macro_f1,
        "per_class": stats,
        "confusion_matrix": cm,
        "labels": list(label_set)
    }


async def main():
    # Allow overriding the samples path via environment variable for expanded datasets
    data_path_env = os.environ.get('EVAL_SAMPLES_PATH')
    if data_path_env and os.path.exists(data_path_env):
        data_path = os.path.abspath(data_path_env)
    else:
        data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "evaluation_samples.csv")
        # Fallback: if running from repo root, try that path
        if not os.path.exists(data_path):
            data_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "evaluation_samples.csv")
        data_path = os.path.abspath(data_path)

    samples = []
    with open(data_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            samples.append({"id": r["id"], "text": r["text"], "label": r["label"].strip().lower()})

    await emotion_engine.initialize()

    # ==========================================
    # MLflow Experiment Setup
    # ==========================================
    if MLFLOW_AVAILABLE:
        mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", "./mlruns"))
        mlflow.set_experiment("MindTrace-Model-Evaluation")
        print("MLflow tracking enabled — experiment: MindTrace-Model-Evaluation")

    golds = []
    preds = []
    details = []

    # Wrap evaluation in an MLflow run
    run_context = mlflow.start_run(run_name="emotion_model_evaluation") if MLFLOW_AVAILABLE else _DummyContext()

    with run_context:
        # Log evaluation parameters
        if MLFLOW_AVAILABLE:
            mlflow.log_params({
                "dataset_path": data_path,
                "sample_count": len(samples),
                "emotion_model": "j-hartmann/emotion-english-distilroberta-base",
                "sentiment_model": "cardiffnlp/twitter-roberta-base-sentiment-latest",
                "gemini_model": "gemini-1.5-flash",
            })

        for s in samples:
            dom, emotions = await analyze_text(s["text"]) 
            pred = dom or "neutral"
            golds.append(s["label"])
            preds.append(pred)
            details.append({"id": s["id"], "text": s["text"], "gold": s["label"], "pred": pred, "emotions": emotions})

        labels = sorted(list(set(golds + preds)))
        metrics = compute_metrics(golds, preds, labels)

        # ==========================================
        # Log metrics to MLflow
        # ==========================================
        if MLFLOW_AVAILABLE:
            # Log top-level metrics
            mlflow.log_metrics({
                "accuracy": metrics["accuracy"],
                "macro_f1": metrics["macro_f1"],
            })

            # Log per-class F1 scores
            for class_name, class_stats in metrics["per_class"].items():
                safe_name = class_name.replace(" ", "_")
                mlflow.log_metrics({
                    f"{safe_name}_precision": class_stats["precision"],
                    f"{safe_name}_recall": class_stats["recall"],
                    f"{safe_name}_f1": class_stats["f1"],
                })

        # Write detailed per-sample results
        out_csv = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "models_evaluation_results.csv")
        out_csv = os.path.abspath(out_csv)
        with open(out_csv, "w", newline='', encoding='utf-8') as f:
            fieldnames = ["id", "text", "gold", "pred", "emotions_json"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for d in details:
                writer.writerow({"id": d["id"], "text": d["text"], "gold": d["gold"], "pred": d["pred"], "emotions_json": json.dumps(d["emotions"])})

        # Write summary JSON
        summary_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "..", "models_evaluation_summary.json")
        summary_path = os.path.abspath(summary_path)
        with open(summary_path, "w", encoding='utf-8') as f:
            json.dump(metrics, f, indent=2)

        # ==========================================
        # Log artifacts to MLflow
        # ==========================================
        if MLFLOW_AVAILABLE:
            mlflow.log_artifact(out_csv)
            mlflow.log_artifact(summary_path)

            # Generate and log confusion matrix plot
            try:
                import matplotlib
                matplotlib.use('Agg')  # Non-interactive backend
                import matplotlib.pyplot as plt
                import numpy as np

                fig, ax = plt.subplots(figsize=(10, 8))
                cm_array = np.array(metrics["confusion_matrix"])
                im = ax.imshow(cm_array, interpolation='nearest', cmap=plt.cm.Blues)
                ax.figure.colorbar(im, ax=ax)
                ax.set(
                    xticks=range(len(labels)),
                    yticks=range(len(labels)),
                    xticklabels=labels,
                    yticklabels=labels,
                    ylabel='True Label',
                    xlabel='Predicted Label',
                    title='Confusion Matrix — MindTrace Emotion Model'
                )
                plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

                # Add text annotations
                thresh = cm_array.max() / 2.
                for i in range(cm_array.shape[0]):
                    for j in range(cm_array.shape[1]):
                        ax.text(j, i, format(cm_array[i, j], 'd'),
                                ha="center", va="center",
                                color="white" if cm_array[i, j] > thresh else "black")
                fig.tight_layout()

                cm_plot_path = os.path.join(os.path.dirname(out_csv), "mlflow_confusion_matrix.png")
                fig.savefig(cm_plot_path, dpi=150)
                plt.close(fig)
                mlflow.log_artifact(cm_plot_path)
                print(f"Confusion matrix plot logged to MLflow: {cm_plot_path}")
            except ImportError:
                print("matplotlib not installed — skipping confusion matrix plot artifact")
            except Exception as plot_err:
                print(f"Could not generate confusion matrix plot: {plot_err}")

    # Print concise report
    print("Evaluation complete. Summary:")
    print(json.dumps(metrics, indent=2))
    print(f"Detailed per-sample results written to: {out_csv}")
    print(f"Summary JSON written to: {summary_path}")
    if MLFLOW_AVAILABLE:
        print("Results logged to MLflow. View with: mlflow ui")


class _DummyContext:
    """No-op context manager when MLflow is not available."""
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass


if __name__ == '__main__':
    asyncio.run(main())
