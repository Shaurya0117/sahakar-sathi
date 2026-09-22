"""
Patent Feature: Decentralized Peer Verification Protocol.

A Byzantine Fault-Tolerant verification system where existing verified
cooperative members can collectively vouch for new workers.

Replaces a single central point of failure (admin) with reputation-weighted
peer consensus.
"""
from typing import Dict, List, Optional
import json
import hashlib
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from app.models.worker import Worker, VerificationStatus


def get_voter_weight(voter: Worker) -> float:
    """
    Calculate the reputation weight of a voter.
    Highly trusted workers have more voting power.
    Weight ranges from 1.0 (new/basic worker) to 3.0 (platinum worker).
    """
    weight = 1.0
    
    # 1. Experience factor
    if voter.total_jobs and voter.total_jobs > 50:
        weight += 0.5
    elif voter.total_jobs and voter.total_jobs > 10:
        weight += 0.2
        
    # 2. Rating factor
    if voter.rating and voter.rating >= 4.5:
        weight += 0.5
        
    # 3. Trust Score factor (Patent #6 integration)
    trust = getattr(voter, "trust_score", 0.0) or 0.0
    if trust >= 85:  # PLATINUM
        weight += 1.0
    elif trust >= 70:  # GOLD
        weight += 0.5
        
    return round(min(3.0, weight), 2)


def submit_peer_vote(db: Session, voter_id: int, candidate_id: int, is_positive: bool) -> Dict:
    """
    Submit a vote for a pending worker.
    """
    voter = db.query(Worker).filter(Worker.id == voter_id).first()
    if not voter or voter.verification_status != VerificationStatus.VERIFIED:
        raise ValueError("Only verified workers can vote.")
        
    if voter.id == candidate_id:
        raise ValueError("Cannot vote for yourself.")
        
    candidate = db.query(Worker).filter(Worker.id == candidate_id).first()
    if not candidate:
        raise ValueError("Candidate worker not found.")
        
    if candidate.verification_status == VerificationStatus.VERIFIED:
        raise ValueError("Candidate is already verified.")

    # Parse existing votes
    votes = []
    if candidate.peer_votes:
        try:
            votes = json.loads(candidate.peer_votes) if isinstance(candidate.peer_votes, str) else candidate.peer_votes
        except Exception:
            votes = []
            
    # Check if voter already voted
    for v in votes:
        if v.get("voter_id") == voter_id:
            raise ValueError("You have already voted for this candidate.")
            
    # Add new vote
    new_vote = {
        "voter_id": voter.id,
        "weight": get_voter_weight(voter),
        "is_positive": is_positive,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    votes.append(new_vote)
    
    # Save back
    candidate.peer_votes = json.dumps(votes) if isinstance(candidate.peer_votes, str) else votes
    flag_modified(candidate, "peer_votes")
    
    # Check if consensus reached
    consensus = calculate_consensus(candidate, votes)
    if consensus.get("is_verified"):
        candidate.verification_status = VerificationStatus.VERIFIED
        # Generate cryptographic verification hash
        hash_input = f"{candidate.id}-{consensus['score']}-{datetime.now().isoformat()}".encode('utf-8')
        candidate.verification_hash = hashlib.sha256(hash_input).hexdigest()
        candidate.peer_consensus_score = consensus["score"]

    db.commit()
    db.refresh(candidate)
    
    return {
        "success": True,
        "consensus_reached": consensus.get("is_verified"),
        "current_score": consensus.get("score"),
        "votes_count": len(votes)
    }


def calculate_consensus(candidate: Worker, votes: List[Dict] = None) -> Dict:
    """
    Calculate the current consensus score.
    Returns verified=True if total positive weight >= threshold (e.g., 3.0)
    and positive weight is > 75% of total weight (Byzantine tolerance).
    """
    if votes is None:
        if candidate.peer_votes:
            try:
                votes = json.loads(candidate.peer_votes) if isinstance(candidate.peer_votes, str) else candidate.peer_votes
            except:
                votes = []
        else:
            votes = []
            
    if not votes:
        return {"is_verified": False, "score": 0.0, "total_votes": 0}
        
    total_weight = sum(v.get("weight", 1.0) for v in votes)
    positive_weight = sum(v.get("weight", 1.0) for v in votes if v.get("is_positive"))
    
    # Calculate score (0-100)
    score = (positive_weight / total_weight) * 100.0 if total_weight > 0 else 0.0
    
    # Thresholds for automatic verification:
    # 1. Must have at least 3.0 total weight worth of votes
    # 2. Score must be >= 75%
    is_verified = total_weight >= 3.0 and score >= 75.0
    
    return {
        "is_verified": is_verified,
        "score": round(score, 1),
        "total_votes": len(votes),
        "total_weight": round(total_weight, 2),
        "positive_weight": round(positive_weight, 2)
    }
