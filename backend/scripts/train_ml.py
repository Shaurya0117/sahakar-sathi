"""
Training Script for Sahakar Sathi ML Module.

Trains:
1. Acceptance Classifier: Predicts probability of job acceptance given worker & offer attributes.
   - Evaluates LogisticRegression, RandomForest, HistGradientBoosting using 5-fold grouped CV.
   - Calibrates best model with CalibratedClassifierCV.
   - Reports ROC-AUC, Accuracy, F1, Brier score vs. majority-class baseline on held-out test.
2. Duration Regressor: Predicts expected service duration (hours) given service type & parameters.
   - Evaluates Ridge, RandomForest, HistGradientBoosting.
   - Reports MAE, RMSE, R-squared vs. service-mean baseline.
3. Computes permutation feature importance on held-out test sets.
4. Generates publication-ready evaluation charts in docs/ml/.
5. Saves serialized models & metrics to backend/app/ml/artifacts/.
"""

import os
import json
import datetime
import numpy as np
import pandas as pd
import joblib
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt

from sklearn.model_selection import GroupKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.inspection import permutation_importance
from sklearn.metrics import (
    roc_auc_score, accuracy_score, f1_score, brier_score_loss,
    roc_curve, confusion_matrix, ConfusionMatrixDisplay,
    mean_absolute_error, root_mean_squared_error, r2_score
)

RANDOM_SEED = 42


def train_acceptance_model(data_path: str, artifacts_dir: str, docs_dir: str):
    print("=" * 60)
    print("1. TRAINING ACCEPTANCE CLASSIFIER")
    print("=" * 60)
    
    df = pd.read_csv(data_path)
    feature_cols = [
        "distance_km",
        "skill_match_score",
        "fatigue_index",
        "rating",
        "experience_years",
        "recent_earnings",
        "job_value",
        "job_intensity",
        "hour_of_day",
        "past_acceptance_rate",
    ]
    target_col = "accepted"
    group_col = "sim_seed"
    
    # 70/15/15 Grouped split based on sim_seed
    unique_seeds = np.sort(df[group_col].unique())
    rng = np.random.default_rng(RANDOM_SEED)
    shuffled_seeds = rng.permutation(unique_seeds)
    
    n_seeds = len(shuffled_seeds)
    n_train = int(0.70 * n_seeds)
    n_val = int(0.15 * n_seeds)
    
    train_seeds = shuffled_seeds[:n_train]
    val_seeds = shuffled_seeds[n_train:n_train + n_val]
    test_seeds = shuffled_seeds[n_train + n_val:]
    
    train_mask = df[group_col].isin(train_seeds)
    val_mask = df[group_col].isin(val_seeds)
    test_mask = df[group_col].isin(test_seeds)
    
    X_train, y_train = df.loc[train_mask, feature_cols], df.loc[train_mask, target_col].values
    train_groups = df.loc[train_mask, group_col].values
    
    X_val, y_val = df.loc[val_mask, feature_cols], df.loc[val_mask, target_col].values
    X_test, y_test = df.loc[test_mask, feature_cols], df.loc[test_mask, target_col].values
    
    print(f"Data split: Train={len(X_train)} (seeds={len(train_seeds)}), "
          f"Val={len(X_val)} (seeds={len(val_seeds)}), "
          f"Test={len(X_test)} (seeds={len(test_seeds)})")
    
    candidate_models = {
        "LogisticRegression": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(max_iter=1000, random_state=RANDOM_SEED))
        ]),
        "RandomForest": RandomForestClassifier(
            n_estimators=100, max_depth=12, random_state=RANDOM_SEED, n_jobs=-1
        ),
        "HistGradientBoosting": HistGradientBoostingClassifier(
            max_iter=100, random_state=RANDOM_SEED
        ),
    }
    
    # 5-fold GroupKFold Cross-Validation on Train Set
    gkf = GroupKFold(n_splits=5)
    cv_scores = {}
    
    for name, model in candidate_models.items():
        fold_aucs = []
        for train_idx, fold_val_idx in gkf.split(X_train, y_train, groups=train_groups):
            X_f_tr, y_f_tr = X_train.iloc[train_idx], y_train[train_idx]
            X_f_val, y_f_val = X_train.iloc[fold_val_idx], y_train[fold_val_idx]
            
            model.fit(X_f_tr, y_f_tr)
            y_pred_proba = model.predict_proba(X_f_val)[:, 1]
            fold_aucs.append(roc_auc_score(y_f_val, y_pred_proba))
            
        mean_auc = float(np.mean(fold_aucs))
        std_auc = float(np.std(fold_aucs))
        cv_scores[name] = {"mean_roc_auc": mean_auc, "std_roc_auc": std_auc}
        print(f"  {name:22s} -> 5-Fold Grouped CV ROC-AUC: {mean_auc:.4f} (+/- {std_auc:.4f})")
        
    best_name = max(cv_scores, key=lambda k: cv_scores[k]["mean_roc_auc"])
    print(f"\nWinning Model: {best_name} (ROC-AUC: {cv_scores[best_name]['mean_roc_auc']:.4f})")
    
    # Fit winner on train set, then calibrate with cv=5
    print("Calibrating model using sigmoid CalibratedClassifierCV (cv=5)...")
    winning_model = candidate_models[best_name]
    calibrated_model = CalibratedClassifierCV(estimator=winning_model, method="sigmoid", cv=5)
    calibrated_model.fit(X_train, y_train)
    
    # Evaluate on held-out test set
    y_test_prob = calibrated_model.predict_proba(X_test)[:, 1]
    y_test_pred = (y_test_prob >= 0.5).astype(int)
    
    test_roc_auc = float(roc_auc_score(y_test, y_test_prob))
    test_acc = float(accuracy_score(y_test, y_test_pred))
    test_f1 = float(f1_score(y_test, y_test_pred))
    test_brier = float(brier_score_loss(y_test, y_test_prob))
    
    # Majority-class baseline
    majority_class = int(y_train.mean() >= 0.5)
    y_base_pred = np.full_like(y_test, fill_value=majority_class)
    y_base_prob = np.full_like(y_test_prob, fill_value=float(y_train.mean()))
    
    base_acc = float(accuracy_score(y_test, y_base_pred))
    base_f1 = float(f1_score(y_test, y_base_pred, zero_division=0))
    base_brier = float(brier_score_loss(y_test, y_base_prob))
    
    print("\nHeld-out Test Set Performance:")
    print(f"  ROC-AUC      : {test_roc_auc:.4f}  (Baseline: 0.5000)")
    print(f"  Accuracy     : {test_acc:.4f}  (Baseline: {base_acc:.4f})")
    print(f"  F1 Score     : {test_f1:.4f}  (Baseline: {base_f1:.4f})")
    print(f"  Brier Score  : {test_brier:.4f}  (Baseline: {base_brier:.4f})")
    
    # Permutation feature importance on test set
    print("\nComputing Permutation Feature Importance (ROC-AUC metric, 10 repeats)...")
    perm_res = permutation_importance(
        calibrated_model, X_test, y_test, scoring="roc_auc", n_repeats=10, random_state=RANDOM_SEED, n_jobs=-1
    )
    
    importances = {}
    for col, mean_imp, std_imp in zip(feature_cols, perm_res.importances_mean, perm_res.importances_std):
        importances[col] = {"mean": float(mean_imp), "std": float(std_imp)}
        
    sorted_features = sorted(importances.items(), key=lambda x: x[1]["mean"], reverse=True)
    print("Top features by permutation importance:")
    for rank, (feat, vals) in enumerate(sorted_features[:5], start=1):
        print(f"  {rank}. {feat:22s} : {vals['mean']:.4f} (+/- {vals['std']:.4f})")
        
    # --- Figures ---
    os.makedirs(docs_dir, exist_ok=True)
    
    # 1. ROC Curve
    fpr, tpr, _ = roc_curve(y_test, y_test_prob)
    plt.figure(figsize=(6, 5))
    plt.plot(fpr, tpr, color="#059669", lw=2, label=f"{best_name} (AUC = {test_roc_auc:.3f})")
    plt.plot([0, 1], [0, 1], color="#9ca3af", lw=1.5, linestyle="--", label="Random Chance (AUC = 0.500)")
    plt.xlim([0.0, 1.0])
    plt.ylim([0.0, 1.05])
    plt.xlabel("False Positive Rate", fontsize=10)
    plt.ylabel("True Positive Rate", fontsize=10)
    plt.title("ROC Curve: Worker Acceptance Model", fontsize=11, fontweight="bold")
    plt.legend(loc="lower right")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(docs_dir, "acceptance_roc_curve.png"), dpi=200)
    plt.close()
    
    # 2. Calibration Curve
    prob_true, prob_pred = calibration_curve(y_test, y_test_prob, n_bins=10)
    plt.figure(figsize=(6, 5))
    plt.plot(prob_pred, prob_true, "s-", color="#2563eb", label="Calibrated Model")
    plt.plot([0, 1], [0, 1], "k--", label="Perfect Calibration")
    plt.xlabel("Mean Predicted Probability", fontsize=10)
    plt.ylabel("Fraction of Positives", fontsize=10)
    plt.title("Calibration Curve (Reliability Diagram)", fontsize=11, fontweight="bold")
    plt.legend(loc="lower right")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(docs_dir, "acceptance_calibration_curve.png"), dpi=200)
    plt.close()
    
    # 3. Confusion Matrix
    cm = confusion_matrix(y_test, y_test_pred)
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=["Decline (0)", "Accept (1)"])
    fig, ax = plt.subplots(figsize=(5, 4.5))
    disp.plot(cmap="Blues", ax=ax, colorbar=False)
    plt.title("Confusion Matrix (Test Set)", fontsize=11, fontweight="bold")
    plt.tight_layout()
    plt.savefig(os.path.join(docs_dir, "acceptance_confusion_matrix.png"), dpi=200)
    plt.close()
    
    # 4. Feature Importance Bar Chart
    feat_names = [f[0] for f in sorted_features]
    feat_means = [f[1]["mean"] for f in sorted_features]
    plt.figure(figsize=(8, 5))
    y_pos = np.arange(len(feat_names))
    plt.barh(y_pos, feat_means, color="#0d9488", align="center")
    plt.yticks(y_pos, feat_names)
    plt.gca().invert_yaxis()
    plt.xlabel("Permutation Importance (Mean ROC-AUC Drop)", fontsize=10)
    plt.title("Feature Importance: Worker Acceptance Model", fontsize=11, fontweight="bold")
    plt.grid(axis="x", alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(docs_dir, "acceptance_feature_importance.png"), dpi=200)
    plt.close()
    
    # Save Model Artifact
    os.makedirs(artifacts_dir, exist_ok=True)
    model_artifact_path = os.path.join(artifacts_dir, "acceptance.joblib")
    joblib.dump(calibrated_model, model_artifact_path)
    print(f"Saved model artifact: {model_artifact_path}")
    
    return {
        "model_name": best_name,
        "calibrated": True,
        "calibration_method": "sigmoid",
        "feature_order": feature_cols,
        "cv_results": cv_scores,
        "test_metrics": {
            "roc_auc": test_roc_auc,
            "accuracy": test_acc,
            "f1_score": test_f1,
            "brier_score": test_brier,
            "baseline_accuracy": base_acc,
            "baseline_f1": base_f1,
            "baseline_brier": base_brier,
        },
        "permutation_importance": importances,
    }


def train_duration_model(data_path: str, artifacts_dir: str, docs_dir: str):
    print("\n" + "=" * 60)
    print("2. TRAINING DURATION REGRESSOR")
    print("=" * 60)
    
    df = pd.read_csv(data_path)
    feature_cols = ["service_type", "job_intensity", "experience_years", "job_value"]
    target_col = "hours"
    
    X = df[feature_cols]
    y = df[target_col].values
    
    # 70/15/15 train/val/test split
    X_train_val, X_test, y_train_val, y_test = train_test_split(
        X, y, test_size=0.15, random_state=RANDOM_SEED
    )
    val_rel_size = 0.15 / 0.85
    X_train, X_val, y_train, y_val = train_test_split(
        X_train_val, y_train_val, test_size=val_rel_size, random_state=RANDOM_SEED
    )
    
    print(f"Data split: Train={len(X_train)}, Val={len(X_val)}, Test={len(X_test)}")
    
    preprocessor = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), ["service_type"]),
        ("num", StandardScaler(), ["job_intensity", "experience_years", "job_value"]),
    ])
    
    candidate_regressors = {
        "Ridge": Pipeline([
            ("pre", preprocessor),
            ("reg", Ridge(alpha=1.0, random_state=RANDOM_SEED))
        ]),
        "RandomForest": Pipeline([
            ("pre", preprocessor),
            ("reg", RandomForestRegressor(n_estimators=100, max_depth=10, random_state=RANDOM_SEED, n_jobs=-1))
        ]),
        "HistGradientBoosting": Pipeline([
            ("pre", preprocessor),
            ("reg", HistGradientBoostingRegressor(max_iter=100, random_state=RANDOM_SEED))
        ]),
    }
    
    val_scores = {}
    for name, pipeline in candidate_regressors.items():
        pipeline.fit(X_train, y_train)
        y_val_pred = pipeline.predict(X_val)
        mae = float(mean_absolute_error(y_val, y_val_pred))
        rmse = float(root_mean_squared_error(y_val, y_val_pred))
        r2 = float(r2_score(y_val, y_val_pred))
        val_scores[name] = {"mae": mae, "rmse": rmse, "r2": r2}
        print(f"  {name:22s} -> Val MAE: {mae:.3f} hrs, RMSE: {rmse:.3f} hrs, R2: {r2:.3f}")
        
    best_name = min(val_scores, key=lambda k: val_scores[k]["mae"])
    print(f"\nWinning Regressor: {best_name} (Val MAE: {val_scores[best_name]['mae']:.3f} hrs)")
    
    best_pipeline = candidate_regressors[best_name]
    # Retrain on full train+val for deployment
    best_pipeline.fit(pd.concat([X_train, X_val]), np.concatenate([y_train, y_val]))
    
    # Evaluate on test set
    y_test_pred = best_pipeline.predict(X_test)
    test_mae = float(mean_absolute_error(y_test, y_test_pred))
    test_rmse = float(root_mean_squared_error(y_test, y_test_pred))
    test_r2 = float(r2_score(y_test, y_test_pred))
    
    # Baseline: Mean duration per service type computed from training set
    train_df = pd.concat([X_train, X_val]).copy()
    train_df["hours"] = np.concatenate([y_train, y_val])
    service_means = train_df.groupby("service_type")["hours"].mean().to_dict()
    overall_mean = float(train_df["hours"].mean())
    
    y_base_pred = np.array([service_means.get(s, overall_mean) for s in X_test["service_type"]])
    base_mae = float(mean_absolute_error(y_test, y_base_pred))
    base_rmse = float(root_mean_squared_error(y_test, y_base_pred))
    base_r2 = float(r2_score(y_test, y_base_pred))
    
    print("\nHeld-out Test Set Performance:")
    print(f"  MAE  : {test_mae:.3f} hrs (Baseline: {base_mae:.3f} hrs)")
    print(f"  RMSE : {test_rmse:.3f} hrs (Baseline: {base_rmse:.3f} hrs)")
    print(f"  R^2  : {test_r2:.3f}     (Baseline: {base_r2:.3f})")
    
    # Permutation feature importance
    print("\nComputing Permutation Feature Importance for Duration Regressor...")
    perm_res = permutation_importance(
        best_pipeline, X_test, y_test, scoring="neg_mean_absolute_error", n_repeats=10, random_state=RANDOM_SEED, n_jobs=-1
    )
    importances = {}
    for col, mean_imp, std_imp in zip(feature_cols, perm_res.importances_mean, perm_res.importances_std):
        importances[col] = {"mean": float(mean_imp), "std": float(std_imp)}
        
    sorted_features = sorted(importances.items(), key=lambda x: x[1]["mean"], reverse=True)
    print("Features by importance (negative MAE impact):")
    for rank, (feat, vals) in enumerate(sorted_features, start=1):
        print(f"  {rank}. {feat:22s} : {vals['mean']:.4f} (+/- {vals['std']:.4f})")
        
    # --- Figures ---
    # 1. Predicted vs Actual Scatter Plot
    plt.figure(figsize=(6, 5))
    plt.scatter(y_test[:800], y_test_pred[:800], alpha=0.35, color="#0284c7", edgecolors="none", s=25)
    lims = [0.0, 7.5]
    plt.plot(lims, lims, "r--", lw=1.5, label="Perfect Fit (y = x)")
    plt.xlabel("Actual Duration (hours)", fontsize=10)
    plt.ylabel("Predicted Duration (hours)", fontsize=10)
    plt.title(f"Predicted vs Actual Duration ({best_name})", fontsize=11, fontweight="bold")
    plt.legend(loc="upper left")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(docs_dir, "duration_predicted_vs_actual.png"), dpi=200)
    plt.close()
    
    # 2. Feature Importance Bar Chart
    plt.figure(figsize=(7, 4))
    feat_names = [f[0] for f in sorted_features]
    feat_means = [f[1]["mean"] for f in sorted_features]
    y_pos = np.arange(len(feat_names))
    plt.barh(y_pos, feat_means, color="#6366f1", align="center")
    plt.yticks(y_pos, feat_names)
    plt.gca().invert_yaxis()
    plt.xlabel("Permutation Importance (Drop in -MAE)", fontsize=10)
    plt.title("Feature Importance: Service Duration Regressor", fontsize=11, fontweight="bold")
    plt.grid(axis="x", alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(docs_dir, "duration_feature_importance.png"), dpi=200)
    plt.close()
    
    # Save Model Artifact
    model_artifact_path = os.path.join(artifacts_dir, "duration.joblib")
    joblib.dump(best_pipeline, model_artifact_path)
    print(f"Saved duration model artifact: {model_artifact_path}")
    
    return {
        "model_name": best_name,
        "feature_order": feature_cols,
        "validation_scores": val_scores,
        "test_metrics": {
            "mae": test_mae,
            "rmse": test_rmse,
            "r2": test_r2,
            "baseline_mae": base_mae,
            "baseline_rmse": base_rmse,
            "baseline_r2": base_r2,
        },
        "service_type_baselines": service_means,
        "permutation_importance": importances,
    }


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ml_data_dir = os.path.join(base_dir, "..", "ml_data")
    artifacts_dir = os.path.join(base_dir, "..", "app", "ml", "artifacts")
    docs_dir = os.path.join(base_dir, "..", "..", "docs", "ml")
    
    acc_path = os.path.join(ml_data_dir, "acceptance_data.csv")
    dur_path = os.path.join(ml_data_dir, "duration_data.csv")
    
    if not os.path.exists(acc_path) or not os.path.exists(dur_path):
        print("Data files not found. Generating them first...")
        import generate_ml_data
        generate_ml_data.main()
        
    acc_results = train_acceptance_model(acc_path, artifacts_dir, docs_dir)
    dur_results = train_duration_model(dur_path, artifacts_dir, docs_dir)
    
    metrics_summary = {
        "trained_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "random_seed": RANDOM_SEED,
        "acceptance_model": acc_results,
        "duration_model": dur_results,
    }
    
    metrics_path = os.path.join(artifacts_dir, "metrics.json")
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics_summary, f, indent=2)
    print(f"\nAll artifacts saved! Metrics summary written to: {metrics_path}")


if __name__ == "__main__":
    main()
