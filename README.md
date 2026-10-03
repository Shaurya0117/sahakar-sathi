# Sahakar Sathi - Project Summary

## Implemented vs Mocked Features

| Feature | Status | Details |
|---------|--------|---------|
| **Bio-Economic Matching Engine** | Implemented | `engine.py` assigns real multi-factor scores based on trust, workload, location, and earnings equality. Fairness rules heavily enforce workload limits. |
| **Privacy-Preserving Proof of Work** | Implemented | Uses `proof_of_work_hash` generated at the client. Anti-replay is enforced server-side using Hamming distance against past completions. |
| **Voice Assistant** | Implemented | Supports fuzzy phonetics for commands (`accept`, `start`, checking jobs/earnings). Uses `SpeechSynthesis` and `webkitSpeechRecognition` to communicate in Hindi. |
| **Byzantine Fault Tolerant Trust** | Implemented | `test_workers.py` proves a sybil attack algorithm with an adaptive damping factor filters out malicious fake reviews. |
| **Simulated Equity / Forecasting** | Implemented | Python script uses Monte-Carlo to project future wealth distributions. |
| **GPS / Nonce / OTP** | Mocked | Defaulted to `False` in the backend. Proof of work currently runs on hashes alone; actual OTP exchange and precise GPS boundary validation is skipped pending full mobile app hooks. |

## Seed Data & The 3-Voter Rule
The tests (`test_matching.py`) and our reset scripts demonstrate the strict `3-voter rule` constraints:
- Unverified workers cannot accept jobs.
- The trust threshold dictates who receives higher tiered jobs.
- Workload limits block assigning jobs to a worker already working at that time.

## Equity Trade-offs
Refer to `equity_simulation_chart.png` in the artifacts for visual proof. The trade-off is clear: strictly enforcing the workload limit caps the most productive workers' earnings, ensuring lower-tier workers gain sufficient experience to level up. Without this limit, the system behaves purely capitalistically and wealth concentrates in the top 10% of workers.
