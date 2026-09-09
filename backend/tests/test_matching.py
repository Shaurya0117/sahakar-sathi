"""
Tests for Explainable AI Worker Matching Engine.

Validates eligibility rules, scoring components, workload fairness,
explainability, endpoint authorization, and ranking.
"""
from fastapi.testclient import TestClient
from app.main import app
from app.models.cooperative import Cooperative
from app.models.service import Service
from app.models.service_request import RequestStatus, ServiceRequest
from app.models.user import User, UserRole
from app.models.worker import AvailabilityStatus, VerificationStatus, Worker
from app.services.matching import (
    calculate_availability_score,
    calculate_experience_score,
    calculate_fairness_score,
    calculate_location_score,
    calculate_rating_score,
    calculate_skill_score,
    calculate_total_score,
    filter_eligible_candidates,
    generate_match_explanation,
    get_matching_recommendations,
)
from tests.conftest import TestingSessionLocal

client = TestClient(app)


def register(email, password="Password1", role="CUSTOMER", name="Test User"):
    return client.post("/api/auth/register", json={
        "name": name,
        "email": email,
        "password": password,
        "role": role,
    })


def login(email, password="Password1"):
    return client.post("/api/auth/login", data={
        "username": email,
        "password": password,
    })


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def setup_matching_test_data():
    """Helper to seed base admin, cooperative, service, and service request."""
    db = TestingSessionLocal()
    admin = User(name="Admin", email="admin_m@test.com", password_hash="hash", role=UserRole.ADMIN)
    db.add(admin)
    db.commit()

    coop = Cooperative(name="Test Coop", location="Noida", admin_id=admin.id)
    db.add(coop)
    db.commit()

    service = Service(name="Electrical Repairs & Maintenance", category="Electrical", description="Wiring repair")
    db.add(service)
    db.commit()

    customer = User(name="Cust", email="cust_m@test.com", password_hash="hash", role=UserRole.CUSTOMER)
    db.add(customer)
    db.commit()

    request = ServiceRequest(
        customer_id=customer.id,
        service_id=service.id,
        cooperative_id=coop.id,
        description="Ceiling fan electrical repair",
        location="Sector 62, Noida",
        preferred_date="2026-08-30",
        preferred_time="10:00",
        status=RequestStatus.PENDING,
    )
    db.add(request)
    db.commit()

    req_id = request.id
    coop_id = coop.id
    service_id = service.id
    admin_id = admin.id
    db.close()
    return admin_id, coop_id, service_id, req_id


def test_verified_worker_can_become_candidate():
    """1. Verified available worker becomes an eligible candidate."""
    _, coop_id, service_id, req_id = setup_matching_test_data()
    db = TestingSessionLocal()

    user = User(name="Worker 1", email="w1@test.com", password_hash="hash", role=UserRole.WORKER)
    db.add(user)
    db.commit()

    worker = Worker(
        user_id=user.id,
        cooperative_id=coop_id,
        profession="Electrician",
        verification_status=VerificationStatus.VERIFIED,
        availability=AvailabilityStatus.AVAILABLE,
        skills=["Wiring"],
    )
    db.add(worker)
    db.commit()

    request = db.query(ServiceRequest).filter(ServiceRequest.id == req_id).first()
    candidates = filter_eligible_candidates(db, request)
    candidate_ids = [c.id for c in candidates]
    assert worker.id in candidate_ids
    db.close()


def test_unverified_worker_excluded():
    """2. Pending/unverified worker is excluded from candidate list."""
    _, coop_id, service_id, req_id = setup_matching_test_data()
    db = TestingSessionLocal()

    user = User(name="Pending Worker", email="wp@test.com", password_hash="hash", role=UserRole.WORKER)
    db.add(user)
    db.commit()

    worker = Worker(
        user_id=user.id,
        cooperative_id=coop_id,
        profession="Electrician",
        verification_status=VerificationStatus.PENDING,
        availability=AvailabilityStatus.AVAILABLE,
        skills=["Wiring"],
    )
    db.add(worker)
    db.commit()

    request = db.query(ServiceRequest).filter(ServiceRequest.id == req_id).first()
    candidates = filter_eligible_candidates(db, request)
    candidate_ids = [c.id for c in candidates]
    assert worker.id not in candidate_ids
    db.close()


def test_rejected_worker_excluded():
    """3. Rejected worker is excluded from candidate list."""
    _, coop_id, service_id, req_id = setup_matching_test_data()
    db = TestingSessionLocal()

    user = User(name="Rejected Worker", email="wr@test.com", password_hash="hash", role=UserRole.WORKER)
    db.add(user)
    db.commit()

    worker = Worker(
        user_id=user.id,
        cooperative_id=coop_id,
        profession="Electrician",
        verification_status=VerificationStatus.REJECTED,
        availability=AvailabilityStatus.AVAILABLE,
        skills=["Wiring"],
    )
    db.add(worker)
    db.commit()

    request = db.query(ServiceRequest).filter(ServiceRequest.id == req_id).first()
    candidates = filter_eligible_candidates(db, request)
    candidate_ids = [c.id for c in candidates]
    assert worker.id not in candidate_ids
    db.close()


def test_unavailable_worker_excluded():
    """4. Unavailable worker is excluded from candidate list."""
    _, coop_id, service_id, req_id = setup_matching_test_data()
    db = TestingSessionLocal()

    user = User(name="Unavailable Worker", email="wu@test.com", password_hash="hash", role=UserRole.WORKER)
    db.add(user)
    db.commit()

    worker = Worker(
        user_id=user.id,
        cooperative_id=coop_id,
        profession="Electrician",
        verification_status=VerificationStatus.VERIFIED,
        availability=AvailabilityStatus.UNAVAILABLE,
        skills=["Wiring"],
    )
    db.add(worker)
    db.commit()

    request = db.query(ServiceRequest).filter(ServiceRequest.id == req_id).first()
    candidates = filter_eligible_candidates(db, request)
    candidate_ids = [c.id for c in candidates]
    assert worker.id not in candidate_ids
    db.close()


def test_worker_from_another_cooperative_excluded():
    """5. Worker belonging to a different cooperative is excluded."""
    _, coop_id, service_id, req_id = setup_matching_test_data()
    db = TestingSessionLocal()

    other_coop = Cooperative(name="Other Coop", location="Delhi")
    db.add(other_coop)
    db.commit()

    user = User(name="Other Coop Worker", email="wother@test.com", password_hash="hash", role=UserRole.WORKER)
    db.add(user)
    db.commit()

    worker = Worker(
        user_id=user.id,
        cooperative_id=other_coop.id,
        profession="Electrician",
        verification_status=VerificationStatus.VERIFIED,
        availability=AvailabilityStatus.AVAILABLE,
        skills=["Wiring"],
    )
    db.add(worker)
    db.commit()

    request = db.query(ServiceRequest).filter(ServiceRequest.id == req_id).first()
    candidates = filter_eligible_candidates(db, request)
    candidate_ids = [c.id for c in candidates]
    assert worker.id not in candidate_ids
    db.close()


def test_relevant_profession_gets_high_skill_score():
    """6. Relevant profession produces a high skill score."""
    service = Service(name="Electrical Repairs & Maintenance", category="Electrical")
    w1 = Worker(profession="Electrician", skills=["Wiring", "Fan Repair"])
    w2 = Worker(profession="Gardener", skills=["Lawn Mowing"])

    s1 = calculate_skill_score(service, w1)
    s2 = calculate_skill_score(service, w2)
    assert s1 >= 70.0
    assert s1 > s2


def test_irrelevant_profession_gets_low_skill_score():
    """7. Irrelevant profession produces a low skill score."""
    service = Service(name="Electrical Repairs & Maintenance", category="Electrical")
    w = Worker(profession="Plumber", skills=["Pipe Fitting"])
    score = calculate_skill_score(service, w)
    assert score < 70.0


def test_relevant_skills_increase_score():
    """8. Additional matching skills increase skill score."""
    service = Service(name="Electrical Repairs & Maintenance", category="Electrical")
    w_basic = Worker(profession="Electrician", skills=[])
    w_skilled = Worker(profession="Electrician", skills=["Wiring", "Electrical", "Maintenance"])

    s_basic = calculate_skill_score(service, w_basic)
    s_skilled = calculate_skill_score(service, w_skilled)
    assert s_skilled > s_basic


def test_same_location_receives_higher_location_score():
    """9. Same location receives higher location score than different location."""
    s_same = calculate_location_score("Sector 62, Noida", "Sector 62, Noida")
    s_diff = calculate_location_score("Sector 62, Noida", "Crossings Republik, Ghaziabad")
    assert s_same == 100.0
    assert s_same > s_diff


def test_rating_normalization_works():
    """10. 5-star rating normalizes to 0-100 score, 0 rating gets neutral score (70.0)."""
    assert calculate_rating_score(Worker(rating=5.0)) == 100.0
    assert calculate_rating_score(Worker(rating=4.0)) == 80.0
    assert calculate_rating_score(Worker(rating=0.0)) == 70.0  # Neutral score


def test_experience_normalization_works():
    """11. Experience normalizes cleanly and caps at 100.0."""
    assert calculate_experience_score(Worker(experience_years=0)) == 30.0
    assert calculate_experience_score(Worker(experience_years=2)) == 60.0
    assert calculate_experience_score(Worker(experience_years=4)) == 80.0
    assert calculate_experience_score(Worker(experience_years=5)) == 100.0
    assert calculate_experience_score(Worker(experience_years=20)) == 100.0


def test_lower_workload_receives_higher_fairness_score():
    """12. Cooperative fairness: worker with lower total_jobs receives higher fairness score."""
    w_low_jobs = Worker(total_jobs=2)
    w_high_jobs = Worker(total_jobs=35)

    f_low = calculate_fairness_score(w_low_jobs)
    f_high = calculate_fairness_score(w_high_jobs)

    assert f_low > f_high
    assert f_low == 95.0


def test_total_score_calculation_is_correct():
    """13. Total score weighted sum calculation is exact."""
    breakdown = {
        "skill_match": 90.0,      # 90 * 0.30 = 27.0
        "location": 80.0,         # 80 * 0.20 = 16.0
        "availability": 100.0,    # 100 * 0.20 = 20.0
        "rating": 96.0,           # 96 * 0.10 = 9.6
        "experience": 80.0,       # 80 * 0.10 = 8.0
        "workload_fairness": 90.0 # 90 * 0.10 = 9.0
    }
    # Sum: 27 + 16 + 20 + 9.6 + 8.0 + 9.0 = 89.6
    total = calculate_total_score(breakdown)
    assert total == 89.6


def test_scores_remain_0_to_100():
    """14. Component and total scores remain strictly between 0 and 100."""
    service = Service(name="Plumbing", category="Plumbing")
    worker = Worker(profession="Plumber", rating=5.0, experience_years=25, total_jobs=0, skills=["Pipe Repair"])

    b = {
        "skill_match": calculate_skill_score(service, worker),
        "location": calculate_location_score("Noida", "Noida"),
        "availability": calculate_availability_score(worker),
        "rating": calculate_rating_score(worker),
        "experience": calculate_experience_score(worker),
        "workload_fairness": calculate_fairness_score(worker),
    }

    for key, val in b.items():
        assert 0.0 <= val <= 100.0

    tot = calculate_total_score(b)
    assert 0.0 <= tot <= 100.0


def test_recommendations_sorted_descending():
    """15. Worker recommendations are returned sorted descending by total score."""
    _, coop_id, service_id, req_id = setup_matching_test_data()
    db = TestingSessionLocal()

    # Worker A: High rating, high experience, low workload
    u_a = User(name="Worker A", email="wa@test.com", password_hash="hash", role=UserRole.WORKER)
    db.add(u_a)
    db.commit()
    w_a = Worker(
        user_id=u_a.id,
        cooperative_id=coop_id,
        profession="Electrician",
        verification_status=VerificationStatus.VERIFIED,
        availability=AvailabilityStatus.AVAILABLE,
        skills=["Wiring", "Electrical"],
        location="Sector 62, Noida",
        rating=4.9,
        experience_years=6,
        total_jobs=2,
    )
    db.add(w_a)

    # Worker B: Low experience, high workload
    u_b = User(name="Worker B", email="wb@test.com", password_hash="hash", role=UserRole.WORKER)
    db.add(u_b)
    db.commit()
    w_b = Worker(
        user_id=u_b.id,
        cooperative_id=coop_id,
        profession="Electrician",
        verification_status=VerificationStatus.VERIFIED,
        availability=AvailabilityStatus.AVAILABLE,
        skills=["Wiring"],
        location="Delhi",
        rating=3.8,
        experience_years=1,
        total_jobs=40,
    )
    db.add(w_b)
    db.commit()

    res = get_matching_recommendations(db, req_id)
    assert res.candidate_count == 2
    assert res.recommendations[0].score >= res.recommendations[1].score
    assert res.recommendations[0].worker_name == "Worker A"
    db.close()


def test_explanations_correspond_to_actual_scores():
    """16. Match explanations are dynamically generated based on score breakdown."""
    service = Service(name="Electrical Repairs & Maintenance", category="Electrical")
    worker = Worker(profession="Electrician", rating=4.8, experience_years=5, total_jobs=3)

    b = {
        "skill_match": 90.0,
        "location": 90.0,
        "availability": 100.0,
        "rating": 96.0,
        "experience": 100.0,
        "workload_fairness": 92.5,
    }

    reasons = generate_match_explanation(b, service, worker, "Sector 62, Noida")
    assert len(reasons) >= 4
    assert any("electrical" in r.lower() or "skill" in r.lower() for r in reasons)
    assert any("workload" in r.lower() for r in reasons)


def test_customer_cannot_access_matching_endpoint():
    """17. Customer receives 403 Forbidden when calling matching API."""
    _, _, _, req_id = setup_matching_test_data()
    register("cust_no_match@test.com", role="CUSTOMER")
    ctoken = login("cust_no_match@test.com").json()["access_token"]

    res = client.get(f"/api/matching/requests/{req_id}", headers=auth_header(ctoken))
    assert res.status_code == 403


def test_worker_cannot_access_matching_endpoint():
    """18. Worker receives 403 Forbidden when calling matching API."""
    _, _, _, req_id = setup_matching_test_data()
    register("worker_no_match@test.com", role="WORKER")
    wtoken = login("worker_no_match@test.com").json()["access_token"]

    res = client.get(f"/api/matching/requests/{req_id}", headers=auth_header(wtoken))
    assert res.status_code == 403


def test_admin_can_access_matching_endpoint():
    """19. Cooperative Admin receives 200 OK and matching recommendations."""
    db = TestingSessionLocal()
    from app.services.auth import create_admin_if_absent
    create_admin_if_absent(db, name="Admin Match", email="admin_match1@test.com", password="AdminPass123")
    db.close()

    atoken = login("admin_match1@test.com", "AdminPass123").json()["access_token"]

    _, _, _, req_id = setup_matching_test_data()
    res = client.get(f"/api/matching/requests/{req_id}", headers=auth_header(atoken))
    assert res.status_code == 200
    data = res.json()
    assert "candidate_count" in data
    assert "recommendations" in data


def test_unknown_request_returns_appropriate_response():
    """20. Unknown request ID returns 404 Not Found."""
    db = TestingSessionLocal()
    from app.services.auth import create_admin_if_absent
    create_admin_if_absent(db, name="Admin Match 2", email="admin_match2@test.com", password="AdminPass123")
    db.close()

    atoken = login("admin_match2@test.com", "AdminPass123").json()["access_token"]

    res = client.get("/api/matching/requests/999999", headers=auth_header(atoken))
    assert res.status_code == 404
    assert res.json()["detail"] == "Service request not found."


def test_request_with_no_eligible_workers_returns_empty_recommendations():
    """21. Request with zero eligible workers returns candidate_count=0 and empty recommendations list."""
    _, coop_id, service_id, req_id = setup_matching_test_data()
    db = TestingSessionLocal()
    from app.services.auth import create_admin_if_absent
    create_admin_if_absent(db, name="Admin Match 3", email="admin_match3@test.com", password="AdminPass123")
    db.close()

    atoken = login("admin_match3@test.com", "AdminPass123").json()["access_token"]

    res = client.get(f"/api/matching/requests/{req_id}", headers=auth_header(atoken))
    assert res.status_code == 200
    data = res.json()
    assert data["candidate_count"] == 0
    assert data["recommendations"] == []


def test_matching_only_uses_workers_from_request_cooperative():
    """22. Matching strictly limits candidate pool to the request's cooperative."""
    db = TestingSessionLocal()
    admin = User(name="Admin X", email="adminx@test.com", password_hash="hash", role=UserRole.ADMIN)
    db.add(admin)
    db.commit()

    coop_a = Cooperative(name="Coop A", location="Noida", admin_id=admin.id)
    coop_b = Cooperative(name="Coop B", location="Delhi")
    db.add(coop_a)
    db.add(coop_b)
    db.commit()

    service = Service(name="Plumbing Services", category="Plumbing")
    db.add(service)
    db.commit()

    cust = User(name="Cust X", email="custx@test.com", password_hash="hash", role=UserRole.CUSTOMER)
    db.add(cust)
    db.commit()

    # Service Request belongs to Coop A
    req = ServiceRequest(
        customer_id=cust.id,
        service_id=service.id,
        cooperative_id=coop_a.id,
        description="Fix pipe leak",
        location="Noida",
        preferred_date="2026-08-30",
        preferred_time="10:00",
        status=RequestStatus.PENDING,
    )
    db.add(req)
    db.commit()

    # Worker 1 belongs to Coop A
    u1 = User(name="Coop A Plumber", email="w_coopa@test.com", password_hash="hash", role=UserRole.WORKER)
    db.add(u1)
    db.commit()
    w1 = Worker(
        user_id=u1.id,
        cooperative_id=coop_a.id,
        profession="Plumber",
        verification_status=VerificationStatus.VERIFIED,
        availability=AvailabilityStatus.AVAILABLE,
        skills=["Pipe Repair"],
    )
    db.add(w1)

    # Worker 2 belongs to Coop B
    u2 = User(name="Coop B Plumber", email="w_coopb@test.com", password_hash="hash", role=UserRole.WORKER)
    db.add(u2)
    db.commit()
    w2 = Worker(
        user_id=u2.id,
        cooperative_id=coop_b.id,
        profession="Plumber",
        verification_status=VerificationStatus.VERIFIED,
        availability=AvailabilityStatus.AVAILABLE,
        skills=["Pipe Repair"],
    )
    db.add(w2)
    db.commit()

    candidates = filter_eligible_candidates(db, req)
    candidate_ids = [c.id for c in candidates]

    assert w1.id in candidate_ids
    assert w2.id not in candidate_ids
    db.close()
