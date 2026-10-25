"""
Unsupervised Review Fraud and Rating Anomaly Model Trainer.

Trains an IsolationForest model on review feature distributions.
Evaluates precision, recall, F1, and ROC-AUC against the hidden synthetic fraud labels.
Saves model to backend/app/ml/artifacts/review_fraud.joblib and updates metrics.json.
"""
import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import classification_report, f1_score, precision_score, recall_score, roc_auc_score

DATA_PATH = Path(__file__).resolve().parent.parent / "ml_data" / "review_fraud_data.csv"
ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "app" / "ml" / "artifacts"
MODEL_PATH = ARTIFACTS_DIR / "review_fraud.joblib"
METRICS_PATH = ARTIFACTS_DIR / "metrics.json"

FEATURE_COLS = [
    "rating_value",
    "review_length",
    "booking_amount",
    "worker_tenure_days",
    "worker_recent_booking_count",
    "rating_deviation_from_worker_mean",
]


def train_review_fraud_detector():
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"Data file not found at {DATA_PATH}. Run generate_review_data.py first.")

    df = pd.read_csv(DATA_PATH)
    X = df[FEATURE_COLS]
    y_true = df["is_fraud_label"].values

    print(f"Loaded {len(df)} samples for review fraud training. Anomaly count: {y_true.sum()} ({y_true.mean():.2%})")

    # Fit Isolation Forest (Unsupervised)
    iso = IsolationForest(
        n_estimators=100,
        contamination=0.08,
        random_state=42,
        n_jobs=-1,
    )
    iso.fit(X)

    # In scikit-learn, -1 indicates anomaly, 1 indicates normal
    raw_preds = iso.predict(X)
    y_pred = (raw_preds == -1).astype(int)

    # Decision function: lower values mean more anomalous
    scores = iso.decision_function(X)
    # Convert to anomaly score where higher = more anomalous
    anomaly_scores = -scores

    auc = float(roc_auc_score(y_true, anomaly_scores))
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))

    print("\n--- Review Fraud Isolation Forest Evaluation ---")
    print(f"ROC-AUC:   {auc:.4f}")
    print(f"Precision: {prec:.4f}")
    print(f"Recall:    {rec:.4f}")
    print(f"F1-Score:  {f1:.4f}")
    print(classification_report(y_true, y_pred, target_names=["Normal", "Anomalous"]))

    # Save model artifact
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(iso, MODEL_PATH)
    print(f"Saved trained IsolationForest model -> {MODEL_PATH}")

    # Append to metrics.json
    metrics_data = {}
    if METRICS_PATH.is_file():
        try:
            with open(METRICS_PATH, "r", encoding="utf-8") as f:
                metrics_data = json.load(f)
        except Exception:
            metrics_data = {}

    metrics_data["review_fraud"] = {
        "model_name": "IsolationForest",
        "contamination": 0.08,
        "n_estimators": 100,
        "features": FEATURE_COLS,
        "roc_auc": round(auc, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "f1": round(f1, 4),
        "sample_count": len(df),
    }

    with open(METRICS_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics_data, f, indent=2)
    print(f"Updated metrics summary -> {METRICS_PATH}")


if __name__ == "__main__":
    train_review_fraud_detector()
