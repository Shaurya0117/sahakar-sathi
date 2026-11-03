# Sahakar Sathi - Project Summary

Demo passwords are for local demos only. Rotate before any real deployment.

## Implemented Features

| Feature | Status | Details |
|---------|--------|---------|
| **Bio-Economic Matching Engine** | Implemented | `engine.py` assigns real multi-factor scores based on trust, workload, location, and earnings equality. Fairness rules enforce workload limits. |
| **Proof of Completion** | Implemented | Job completion is verified with a signed proof bundle. |
| **Voice Assistant** | Implemented | Supports fuzzy phonetics for commands (`accept`, `start`, checking jobs/earnings). Uses `SpeechSynthesis` and `webkitSpeechRecognition` to communicate in Hindi. |
| **Bayesian Trust Score** | Implemented | Reputation scoring incorporates weighted history and exponential decay. |
| **Simulated Equity / Forecasting** | Implemented | Python script uses Monte-Carlo to project future wealth distributions. |

## Seed Data & The 3-Voter Rule
The tests (`test_matching.py`) and our reset scripts demonstrate the strict `3-voter rule` constraints:
- Unverified workers cannot accept jobs.
- The trust threshold dictates who receives higher tiered jobs.
- Workload limits block assigning jobs to a worker already working at that time.

## Running the Backend

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

> **Security Note on Webhook Secrets:** If `SMS_WEBHOOK_SECRET` is passed as a query parameter (`/api/sms/reply?secret=...`), start the server with `--no-access-log` (`python -m uvicorn app.main:app --no-access-log --port 8000`) so Uvicorn does not log the secret in console access logs. Reverse proxies and tunneling tools (like ngrok) also log query strings, so prefer custom header `X-Webhook-Secret` whenever your SMS gateway app supports it.

## Equity Trade-offs
Refer to `equity_simulation_chart.png` in the artifacts for visual proof. The trade-off is clear: strictly enforcing the workload limit caps the most productive workers' earnings, ensuring lower-tier workers gain sufficient experience to level up. Without this limit, the system behaves purely capitalistically and wealth concentrates in the top 10% of workers.
