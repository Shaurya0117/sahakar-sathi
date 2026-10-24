# Machine Learning Module Report: Sahakar Sathi

**Project Title:** Multi-Objective Fair Gig Dispatching with Calibrated Machine Learning Tie-Breaking  
**Application:** Sahakar Sathi Cooperative Gig Platform  
**Target Audience:** Academic Evaluators and Mini-Project Examination Committee  
**Authors:** Cooperative Engineering Team  
**Date:** October 2026  

---

## 1. Problem Statement

Gig economy platforms typically optimize matching purely for platform efficiency—maximizing corporate margin or minimizing immediate delivery latency. In contrast, **Sahakar Sathi** is an autonomous worker cooperative designed to balance service quality, worker livelihoods, and long-term health.

However, matching in real-world gig environments introduces two opposing hazards:

1. **The Fragility of Pure Rule-Based Matching:**
   A deterministic multi-factor scoring formula (weighting skills, location, availability, rating, experience, and economic deficit) makes static assumptions about worker willingness. If the engine dispatches a job to a top-ranked worker who is personally fatigued, working late hours, or sent across town for low remuneration, that worker is likely to decline. Every rejected offer triggers sequential re-dispatching, inflating booking latency and degrading customer retention.

2. **The Injustice of End-to-End Pure Machine Learning Matching:**
   Conversely, training an end-to-end ML model (such as a neural network or greedy bandit) to directly assign jobs creates acute algorithmic bias:
   - **Feedback Loops:** Highly active workers receive all subsequent jobs because their historical acceptance probability is high.
   - **Gini Explosion:** Workers needing income who decline distant or low-paying jobs are systematically starved of future offers.
   - **Health Violations:** An algorithm optimizing short-term acceptance will ruthlessly overwork reliable workers past physical exhaustion caps.

**The Hybrid Cooperative Solution:**  
Sahakar Sathi preserves the **six-factor cooperative allocation policy** as the primary sovereign decision-maker. Machine learning is restricted to a **bounded tie-breaker**: when multiple verified, qualified workers have virtually identical multi-factor scores, the platform breaks the tie in favor of the worker most likely to accept.

---

## 2. Architecture and Non-Interference Guarantee

### System Architecture
The dispatch pipeline follows a strict hierarchical filtering architecture:

```
[ Incoming Service Request ]
            │
            ▼
[ Candidate Filtering & Eligibility ]
   - Sector / Trade Match
   - KYC Verification (VERIFIED status)
   - Availability Flag (AVAILABLE)
            │
            ▼
[ Hard Safety Floor: Fatigue Cap Check ]
   - Exponential Load Decay over 7 days: Load = Σ (Intensity × Hours × 0.8^days_ago)
   - Fatigue Index = min(100, Load / 18.0 × 100)
   - IF Fatigue Index >= 80.0 ──► WORKER HARD BLOCKED (Excluded from Pool)
            │
            ▼
[ Deterministic 6-Factor Scoring ]
   - Skill Match (30%) + Location (20%) + Availability (20%)
   - Rating (10%) + Experience (10%) + Workload Fairness (10%)
            │
            ▼
[ Deterministic Candidate Ranking ]
   - Candidates sorted descending by Score
            │
            ▼
[ Decision Gate: Score Margin <= 2.0 within Top-3? ]
      │                                       │
     NO (Clear Winner)                       YES (Tie-Break Condition)
      │                                       │
      ▼                                       ▼
[ Dispatched in Deterministic Order ]    [ Calibrated ML Acceptance Inference ]
                                          - Re-order ONLY candidates in margin window
                                          - Highest predicted probability offered first
                                          - Remaining candidates maintain score ranks
```

### Non-Interference Mathematical Proof & Safety Guarantees
1. **Safety Floor Invariance:** The fatigue threshold ($FatigueIndex \ge 80.0$) and peer verification requirements execute *prior* to scoring and ML inference. A fatigued or unverified candidate is excluded from the candidate list entirely; the ML module has zero mathematical pathway to promote or evaluate an excluded worker.
2. **Locality Invariance:** Candidates ranked $4^{\text{th}}$ or lower ($k > 3$) and candidates whose multi-factor score differs from the top score by more than $\delta = 2.0$ points are strictly invariant under ML inference. Formally:
   $$\forall i, j \notin \text{TieGroup}, \quad \text{Rank}(i) < \text{Rank}(j) \iff \text{Score}(i) > \text{Score}(j)$$
3. **Graceful Degradation:** If `ML_ENABLED=False`, or if any model artifact fails checksum or load validation, the tie-breaking block is skipped, yielding exact equivalence to the baseline rule-based dispatcher.

---

## 3. Dataset Description

To train the models without harvesting proprietary user data or relying on costly third-party telemetry, synthetic datasets ground-truthed on empirical labor ergonomics were generated via `backend/scripts/generate_ml_data.py`:

| Dataset | Sample Count | Target Variable | Feature Count | Grouping Variable |
|:---|:---:|:---|:---:|:---:|
| **Acceptance Dataset** | 30,000 | `accepted` $\in \{0, 1\}$ | 10 features | `sim_seed` (100 distinct groups) |
| **Duration Dataset** | 15,000 | `hours` $\in [0.5, 8.0]$ | 4 features | Random 70/15/15 partition |

### Feature Space for Acceptance Classification:
- `distance_km`: Haversine distance from worker home base to job site (0.5 to 25.0 km).
- `skill_match_score`: Deterministic skill compatibility percentage (50.0 to 100.0).
- `fatigue_index`: 7-day decaying physical strain metric (0.0 to 85.0).
- `rating`: Worker peer and customer rating (3.0 to 5.0 stars).
- `experience_years`: Verified industry experience (0 to 15 years).
- `recent_earnings`: Rolling 10-booking income in Indian Rupees (₹0 to ₹7,500).
- `job_value`: Gross booking price (₹300 to ₹800).
- `job_intensity`: Physical difficulty factor based on trade (0.50 to 0.85).
- `hour_of_day`: Dispatch timestamp (6:00 to 22:00 hours).
- `past_acceptance_rate`: Historical acceptance frequency (0.0 to 1.0).

### Data Leakage Prevention (Grouped Splitting):
Gig simulation benchmarks reuse underlying seeds to generate market conditions. Splitting offers uniformly at random would allow observations sharing identical simulation seeds to appear across train, validation, and test sets, causing severe optimistic data leakage.  
To prevent this, `generate_ml_data.py` assigns a `sim_seed` (0 to 99) to each offer. A **GroupShuffleSplit** guarantees:
$$\text{Seeds}(\text{Train}) \cap \text{Seeds}(\text{Val}) = \emptyset, \quad \text{Seeds}(\text{Train}) \cap \text{Seeds}(\text{Test}) = \emptyset, \quad \text{Seeds}(\text{Val}) \cap \text{Seeds}(\text{Test}) = \emptyset$$
- **Train partition:** 21,141 rows (70 seeds)
- **Validation partition:** 4,348 rows (15 seeds)
- **Test partition:** 4,511 rows (15 seeds)

---

## 4. Acceptance Prediction Model

### Model Selection via 5-Fold Grouped Cross-Validation
Three candidate model families were evaluated across 5 grouped folds on the training partition:

| Model Architecture | Mean 5-Fold ROC-AUC | Std ROC-AUC | Outcome |
|:---|:---:|:---:|:---:|
| **Logistic Regression** (Standardized) | 0.9285 | $\pm 0.0035$ | Baseline linear reference |
| **Random Forest Classifier** (100 Trees, Depth 10) | 0.9259 | $\pm 0.0037$ | Competitive ensemble |
| **HistGradientBoostingClassifier** | **0.9348** | $\pm 0.0043$ | **Winner (Selected)** |

### Probability Calibration
Raw gradient boosting predictions often exhibit miscalibrated confidence scores near 0 and 1. To ensure probabilities correspond to genuine empirical rates, the winning model was calibrated using **Sigmoid CalibratedClassifierCV** with 5-fold cross-validation.

### Held-Out Test Evaluation (4,511 Unseen Offers)
Metrics on the strictly held-out test partition demonstrate strong discrimination and probability reliability:

| Metric | Calibrated HistGradientBoosting | Majority Baseline | Interpretation |
|:---|:---:|:---:|:---|
| **ROC-AUC** | **0.9441** | 0.5000 | Excellent class separability across thresholds |
| **Accuracy** | **86.17%** | 52.29% | +33.88% improvement over constant predictor |
| **F1-Score** | **0.8683** | 0.6868 | High harmonic balance of precision and recall |
| **Brier Score** | **0.0957** | 0.2495 | Sharp, well-calibrated probabilistic confidence |

### Permutation Feature Importance
Permutation importance computes the drop in ROC-AUC when a feature's values are randomly shuffled on the test set:

| Feature | Importance Drop (ROC-AUC) | Standard Deviation |
|:---|:---:|:---:|
| `fatigue_index` | **+0.1324** | $\pm 0.0034$ |
| `distance_km` | **+0.1223** | $\pm 0.0032$ |
| `job_value` | **+0.0742** | $\pm 0.0028$ |
| `recent_earnings` | **+0.0467** | $\pm 0.0025$ |
| `skill_match_score` | **+0.0364** | $\pm 0.0026$ |
| `past_acceptance_rate` | **+0.0353** | $\pm 0.0018$ |
| `rating` | **+0.0325** | $\pm 0.0024$ |
| `experience_years` | **+0.0142** | $\pm 0.0013$ |
| `hour_of_day` | **+0.0132** | $\pm 0.0009$ |
| `job_intensity` | **+0.0052** | $\pm 0.0006$ |

*Insight:* Worker fatigue and travel distance dominate worker decisions, validating the cooperative's foundational principle that excessive commute and physical strain are primary drivers of gig rejection.

### Model Evaluation Visualizations

![Acceptance ROC Curve](ml/acceptance_roc_curve.png)
*Figure 1: Receiver Operating Characteristic (ROC) curve showing an AUC of 0.9441 on held-out test data.*

![Acceptance Calibration Curve](ml/acceptance_calibration_curve.png)
*Figure 2: Reliability diagram demonstrating close alignment between predicted probability and observed fraction of positives.*

![Acceptance Confusion Matrix](ml/acceptance_confusion_matrix.png)
*Figure 3: Confusion matrix at 0.5 threshold illustrating 86.17% overall accuracy.*

![Acceptance Feature Importance](ml/acceptance_feature_importance.png)
*Figure 4: Permutation feature importances confirming fatigue index and commute distance as chief drivers.*

---

## 5. Duration Prediction Model

### Problem & Objective
When scheduling bookings and updating worker fatigue capacity, service records frequently omit exact duration. The duration regressor predicts service duration in hours given service type, intensity, worker experience, and job valuation.

### Candidate Regressor Comparison (Validation Set)
| Architecture | Validation MAE (hrs) | Validation RMSE (hrs) | Validation $R^2$ |
|:---|:---:|:---:|:---:|
| **Ridge Regression** | 0.2586 | 0.3246 | 0.8766 |
| **Random Forest Regressor** | 0.2524 | 0.3159 | 0.8831 |
| **HistGradientBoostingRegressor** | **0.2452** | **0.3072** | **0.8884** |

### Held-Out Test Evaluation (2,250 Unseen Jobs)
| Metric | HistGradientBoosting Regressor | Dummy Mean Baseline | Improvement |
|:---|:---:|:---:|:---:|
| **Mean Absolute Error (MAE)** | **0.2452 hrs (14.7 mins)** | 0.3773 hrs (22.6 mins) | -35.0% error reduction |
| **Root Mean Squared Error (RMSE)** | **0.3072 hrs (18.4 mins)** | 0.4807 hrs (28.8 mins) | -36.1% error reduction |
| **Coefficient of Determination ($R^2$)** | **0.8884** | 0.7252 | High explained variance |

### Duration Permutation Feature Importance
1. `service_type` (+0.6837): Trade category establishes the baseline workload (e.g. Painting vs. Plumbing).
2. `job_value` (+0.1366): Higher-priced requests denote complex, multi-stage tasks.
3. `experience_years` (+0.1174): Veteran workers complete tasks significantly faster.
4. `job_intensity` (+0.0387): Physically demanding tasks require scheduled rest intervals.

### Duration Visualizations

![Duration Predicted vs Actual](ml/duration_predicted_vs_actual.png)
*Figure 5: Predicted vs. Actual service duration in hours, showing tight correlation along the ideal line.*

![Duration Feature Importance](ml/duration_feature_importance.png)
*Figure 6: Permutation feature importance for service duration estimation.*

---

## 6. Simulation Results

To measure whether ML tie-breaking creates measurable operational advantages without compromising equity, an extensive 100-seed simulation was executed:
- **Simulation Setup:** 100 seeds (0 to 99), 30 workers, 200 service requests per seed (20,000 total dispatch interactions).
- **Escalation Protocol:** The top candidate is offered the job. If rejected (evaluated via the hidden logistic rule with an independent random generator), the offer escalates to the second candidate, and so on.

### 100-Seed Comparison Table

| Metric | Rule-Only Baseline | Matcher + ML Tie-Break | Paired Difference (ML - Rule) | 95% Bootstrap CI (10,000 resamples) |
|:---|:---:|:---:|:---:|:---:|
| **First-Offer Acceptance Rate** | $81.23\% \pm 3.62\%$ | **$82.34\% \pm 3.03\%$** | **$+1.10\%$** | **$[+0.72\%, +1.49\%]$** |
| **Average Offers per Job** | $1.254 \pm 0.051$ | **$1.242 \pm 0.049$** | **$-0.011$** | **$[-0.017, -0.005]$** |
| **Earnings Gini Inequality** | $0.2663 \pm 0.0389$ | **$0.2538 \pm 0.0365$** | **$-0.0125$** | **$[-0.0172, -0.0078]$** |
| **Average Travel Distance** | $2.64 \pm 0.17\text{ km}$ | $2.74 \pm 0.16\text{ km}$ | $+0.10\text{ km}$ | $[+0.08\text{ km}, +0.11\text{ km}]$ |
| **Skill-Match Rate** | $99.91\% \pm 0.26\%$ | $99.90\% \pm 0.30\%$ | $-0.01\%$ | $[-0.05\%, +0.04\%]$ |

### Academic Discussion of Simulation Findings
1. **Statistically Significant Acceptance Uplift:** First-offer acceptance improves by $+1.10\%$ (95% CI: $[+0.72\%, +1.49\%]$), eliminating dozens of rejected offers and customer waiting delays per 1,000 requests.
2. **Equity is Preserved (and Slightly Enhanced):** The Gini coefficient of worker income decreases from $0.2663$ to $0.2538$ ($\Delta = -0.0125$, 95% CI: $[-0.0172, -0.0078]$). Breaking ties in favor of workers who are eager and available helps equalize completed earnings.
3. **Modest Logistics Trade-Off:** Travel distance increases by a negligible 100 meters ($2.64\text{ km} \to 2.74\text{ km}$), because the engine occasionally selects a worker 200 meters farther away if that worker has lower fatigue and higher willingness to complete the task.
4. **Zero Skill Degradation:** The skill-match rate remains essentially perfect at $99.90\%$ vs $99.91\%$ (zero crossing within bootstrap confidence interval).

---

## 7. Distribution Shift Test

In production, worker preferences drift due to inflation, fuel price swings, or seasonal weather. To verify robust generalization, we subjected the models to a **$\pm 30\%$ distribution shift**:
- Distance and fatigue rejection penalties increased by $+30\%$.
- Economic sensitivity increased by $+30\%$.
- Wage incentives decreased by $-30\%$.
- Random noise variance increased from $\sigma=0.5$ to $\sigma=0.75$.
- **Crucial Rule:** The ML models were evaluated directly **WITHOUT RETRAINING**.

### Results under $\pm 30\%$ Distribution Shift (100 Seeds)

| Metric | Rule-Only Baseline | Matcher + ML Tie-Break | Paired Difference (ML - Rule) | 95% Bootstrap CI (10,000 resamples) |
|:---|:---:|:---:|:---:|:---:|
| **First-Offer Acceptance Rate** | $80.40\% \pm 3.08\%$ | **$81.34\% \pm 3.08\%$** | **$+0.94\%$** | **$[+0.56\%, +1.32\%]$** |
| **Average Offers per Job** | $1.268 \pm 0.046$ | **$1.256 \pm 0.050$** | **$-0.012$** | **$[-0.019, -0.006]$** |
| **Earnings Gini Inequality** | $0.2579 \pm 0.0393$ | **$0.2474 \pm 0.0371$** | **$-0.0104$** | **$[-0.0148, -0.0060]$** |
| **Average Travel Distance** | $2.65 \pm 0.17\text{ km}$ | $2.74 \pm 0.17\text{ km}$ | $+0.09\text{ km}$ | $[+0.08\text{ km}, +0.11\text{ km}]$ |
| **Skill-Match Rate** | $99.91\% \pm 0.26\%$ | $99.89\% \pm 0.29\%$ | $-0.02\%$ | $[-0.08\%, +0.04\%]$ |

### Robustness Takeaway
Even when workers became significantly more sensitive to fatigue and commute costs, the ML tie-breaker maintained a statistically significant $+0.94\%$ acceptance advantage without a single retraining cycle. Because ML only operates on narrow ties within the top 3 candidates, out-of-distribution noise cannot destabilize platform allocations.

---

## 8. Failure Modes and Safety Bounds

| Hazard Scenario | System Response | Underlying Mechanism |
|:---|:---|:---|
| **Model files deleted or unreadable** | Silent fallback to rule-based ranking | `predictor.py` wraps file loads in `try/except`; missing models log a warning and return `None`. |
| **Corrupted model artifacts** | Zero system crash; fallback activated | Deserialization errors are caught cleanly, leaving `_acceptance_model = None`. |
| **`ML_ENABLED = False` in config** | Pure rule-based dispatching | Check bypassed before inference; `ml_used` set to `False`. |
| **Input features outside range** | Hard numerical clipping | Features are clipped via `np.clip` (e.g. distance $\in [0, 50]$, fatigue $\in [0, 100]$). |
| **Worker fatigue $> 80.0$** | Hard exclusion from matching pool | Enforced in candidate discovery *before* scoring. ML cannot inspect or promote fatigued workers. |
| **Unverified worker status** | Complete exclusion from candidate pool | Candidate filter enforces `VerificationStatus.VERIFIED` prior to scoring. |

---

## 9. Limitations and Honest Assessment

An honest academic evaluation requires acknowledging the limitations of this implementation:

1. **Synthetic Data Substrate:**  
   The training and evaluation data are generated from an explicit logistic formulation. While based on labor research regarding fatigue decay and travel friction, real human behavior includes unmodeled confounding factors (e.g., weather anomalies, familial emergencies, multi-app gigging).
2. **Exploration vs. Exploitation Limits:**  
   The tie-breaking policy currently exploits the model greedily ($P(\text{accept})$ ranking). In a live platform, an exploration mechanism (e.g., $\epsilon$-greedy exploration or Upper Confidence Bound dispatching) would be required to avoid cold-start bias against newly onboarded workers who lack extensive acceptance history.
3. **Bounded Impact by Design:**  
   Because ML is strictly bounded to a $2.0$-point score margin among top-3 candidates, the absolute acceptance rate uplift is moderate ($+1.10\%$). This is intentional: sacrificing cooperative equity for a larger acceptance jump would violate the platform's constitutional mission.

---

## 10. Mini Project Takeaways

1. **Domain-Constrained ML is Superior to Unconstrained ML:**  
   Allowing ML to govern the entire decision space in socio-technical platforms produces toxic externalities (monopolized income, worker burnout). Constraining ML to operate inside rule-governed safety corridors produces the ideal synthesis of fairness and operational efficiency.
2. **Probabilistic Calibration is Essential:**  
   Raw classification scores are inadequate for operational decisions. Using Platt/Sigmoid calibration transformed raw tree scores into trustworthy probabilities, enabling sound thresholding and tie-breaking.
3. **Data Partition Hygiene Matters:**  
   Grouped cross-validation on simulation seeds proved indispensable. Standard random splits would have reported misleadingly high ROC-AUC due to cross-offer seed leakage.
4. **Reproducibility Builds Trust:**  
   Fixing random seeds, logging permutation importance, and calculating 10,000-resample bootstrap confidence intervals provides transparent, verifiable evidence for faculty examination.
