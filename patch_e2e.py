import sys
with open("backend/scripts/e2e_smoke.py", "r", encoding="utf-8") as f:
    content = f.read()

vote_logic = """
    print("9. Peer Verification Flow: ", end="")
    res = client.post("/api/auth/login", data={"username": "pending@test.com", "password": "pw"})
    if res.status_code == 200:
        cand_token = res.json()["access_token"]
        res = client.get("/api/workers/me", headers=auth(cand_token))
        cand_id = res.json()["id"]
        
        voter_emails = ["vishal.electrician@sahakarsathi.demo", "amit.electrician@sahakarsathi.demo", "vikas.plumber@sahakarsathi.demo"]
        for email in voter_emails:
            login_res = client.post("/api/auth/login", data={"username": email, "password": "Worker@1234"})
            v_token = login_res.json()["access_token"]
            v_res = client.post(f"/api/workers/{cand_id}/peer-verify", json={"vote": 1, "comments": "Looks good"}, headers=auth(v_token))
            
        final_res = client.get("/api/workers/me", headers=auth(cand_token))
        if final_res.json()["verification_status"] == "VERIFIED":
            print("PASS (3 votes reached)")
        else:
            print(f"FAIL (Not verified after 3 votes, status: {final_res.json()[
verification_status]})")
    else:
        print("SKIP (Pending worker not found)")

    print("\\n--- E2E Smoke Test Finished Successfully ---")
"""

content = content.replace("if __name__ == \"__main__\":", vote_logic + "\nif __name__ == \"__main__\":")

with open("backend/scripts/e2e_smoke.py", "w", encoding="utf-8") as f:
    f.write(content)

