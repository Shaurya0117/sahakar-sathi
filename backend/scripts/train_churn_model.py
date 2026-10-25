"""
Train the worker churn prediction model.

- Loads backend/ml_data/churn_data.csv
- 70/15/15 stratified split (random_state=42)
- HistGradientBoostingClassifier wrapped with CalibratedClassifierCV
- Saves model artifact to backend/app/ml/artifacts/churn.joblib
- Appends "churn" key to backend/app/ml/artifacts/metrics.json
"""
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.model_selection import train_test_split

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

DATA_PATH = BACKEND_DIR / "ml_data" / "churn_data.csv"
ARTIFACTS_DIR = BACKEND_DIR / "app" / "ml" / "artifacts"
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
MODEL_PATH = ARTIFACTS_DIR / "churn.joblib"
METRICS_PATH = ARTIFACTS_DIR / "metrics.json"

FEATURE_COLS = [
    "days_since_last_booking",
    "bookings_last_30d",
    "earnings_last_30d",
    "acceptance_rate",
    "avg_fatigue_index",
    "rating",
    "experience_years",
    "days_on_platform",
    "earnings_trend",
]
LABEL_COL = "churned"

print(f"Loading data from {DATA_PATH} ...")
df = pd.read_csv(DATA_PATH)
X = df[FEATURE_COLS]
y = df[LABEL_COL]

# 70/15/15 stratified split: first split off 30%, then halve that
X_train, X_temp, y_train, y_temp = train_test_split(
    X, y, test_size=0.30, random_state=42, stratify=y
)
X_val, X_test, y_val, y_test = train_test_split(
    X_temp, y_temp, test_size=0.50, random_state=42, stratify=y_temp
)

print(f"Train: {len(X_train)}, Val: {len(X_val)}, Test: {len(X_test)}")

# Train base model
base_clf = HistGradientBoostingClassifier(random_state=42, max_iter=200)
calibrated_clf = CalibratedClassifierCV(base_clf, method="sigmoid", cv=5)
calibrated_clf.fit(X_train, y_train)

# Evaluate on test set
y_pred = calibrated_clf.predict(X_test)
y_prob = calibrated_clf.predict_proba(X_test)[:, 1]

roc_auc = float(roc_auc_score(y_test, y_prob))
f1 = float(f1_score(y_test, y_pred))
accuracy = float(accuracy_score(y_test, y_pred))
churn_rate_train = float(y_train.mean())
churn_rate_test = float(y_test.mean())

print("\n=== Churn Model Evaluation (Test Set) ===")
print(f"ROC-AUC:         {roc_auc:.4f}")
print(f"F1 Score:        {f1:.4f}")
print(f"Accuracy:        {accuracy:.4f}")
print(f"Churn rate train:{churn_rate_train:.3f}")
print(f"Churn rate test: {churn_rate_test:.3f}")

# Save model
joblib.dump(calibrated_clf, MODEL_PATH)
print(f"\nModel saved to {MODEL_PATH}")

# Update metrics.json
metrics = {}
if METRICS_PATH.is_file():
    try:
        with open(METRICS_PATH, "r", encoding="utf-8") as f:
            metrics = json.load(f)
    except Exception:
        metrics = {}

metrics["churn"] = {
    "roc_auc": round(roc_auc, 4),
    "f1": round(f1, 4),
    "accuracy": round(accuracy, 4),
    "churn_rate_train": round(churn_rate_train, 4),
    "churn_rate_test": round(churn_rate_test, 4),
}

with open(METRICS_PATH, "w", encoding="utf-8") as f:
    json.dump(metrics, f, indent=2)

print(f"Metrics appended to {METRICS_PATH}")
print("\nDone.")
