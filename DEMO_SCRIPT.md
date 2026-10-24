# Demo Script: Sahakar Sathi

**Preparation:**
1. Start the backend: `cd backend && .\venv\Scripts\uvicorn app.main:app --reload`
2. Start the frontend: `cd frontend && npm run dev`
3. If needed, reset the demo DB: `$env:PYTHONPATH="."; .\venv\Scripts\python scripts/reset_demo.py`

**Act 1: The Bio-Economic Match**
- Open the Admin / Cooperative Dashboard (Login as Cooperative Admin).
- Click on "Auto-Assign" for a pending booking.
- Point out the **Bio-Economic Matching Breakdown**: Show how the score sums to 1.0.

**Act 2: The Voice Assistant**
- Open the Worker Portal (Login as `vishal@test.com`, pw: `password`).
- Wait for the voice assistant greeting.
- Click the mic and say "Accept" (or "स्वीकार करो"). Observe the yes/no confirmation prompt. 
- Say "No" to demonstrate the cancel path. 
- Say "Accept" again, then say "Yes" to accept the job.
- Say "Start" and confirm with "Yes".

**Act 3: Verification**
- While in the Active Job view as the worker, click **Complete Job**.
- Job completion is verified with a signed proof bundle.

**Act 4: Worker Profile & Fatigue**
- Go to the Worker Profile tab.
- Demonstrate the real-time calculated `Fatigue Index` and the `Trust Score Breakdown` ensuring no single factor dictates their livelihood.
