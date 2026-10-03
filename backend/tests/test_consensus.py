import pytest
from app.services.peer_verification import calculate_consensus
from app.models.worker import Worker

def test_calculate_consensus_minimum_voters():
    candidate = Worker(id=1)
    
    # 2 Voters, both Platinum (weight 3.0), both Yes.
    # Total weight = 6.0, Score = 100%. 
    # But voters < 3, so should NOT be verified.
    votes = [
        {"voter_id": 2, "weight": 3.0, "is_positive": True},
        {"voter_id": 3, "weight": 3.0, "is_positive": True}
    ]
    
    result = calculate_consensus(candidate, votes)
    assert result["is_verified"] == False
    assert result["total_votes"] == 2

def test_calculate_consensus_success():
    candidate = Worker(id=1)
    
    # 3 Voters. Total weight = 3.0, all yes
    votes = [
        {"voter_id": 2, "weight": 1.0, "is_positive": True},
        {"voter_id": 3, "weight": 1.0, "is_positive": True},
        {"voter_id": 4, "weight": 1.0, "is_positive": True}
    ]
    
    result = calculate_consensus(candidate, votes)
    assert result["is_verified"] == True
    assert result["score"] == 100.0
