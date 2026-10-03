import pytest
from app.services.trust_score import _calculate_satisfaction, _calculate_reliability
from app.models.worker import Worker

class MockDB:
    def query(self, *args, **kwargs):
        class MockQuery:
            def filter(self, *args, **kwargs): return self
            def scalar(self): return None
            def first(self): return None
        return MockQuery()

def test_trust_score_satisfaction_new_worker():
    db = MockDB()
    worker = Worker(id=1)
    score = _calculate_satisfaction(db, worker)
    # Bayesian average with n=0 should return 70.0 (3.5/5 * 100)
    assert score == 70.0

def test_trust_score_reliability_no_jobs():
    db = MockDB()
    worker = Worker(id=1)
    score = _calculate_reliability(db, worker)
    # No jobs assigned means 60.0
    assert score == 60.0
