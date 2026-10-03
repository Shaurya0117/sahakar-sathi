
with open("backend/scripts/e2e_smoke.py", "r", encoding="utf-8") as f:
    content = f.read()

content = content.replace("f\"/api/workers/{cand_id}/peer-verify\", json={\"vote\": 1, \"comments\": \"Looks good\"}", "\"/api/peer-verification/vote\", json={\"candidate_id\": cand_id, \"is_positive\": True}")

with open("backend/scripts/e2e_smoke.py", "w", encoding="utf-8") as f:
    f.write(content)

