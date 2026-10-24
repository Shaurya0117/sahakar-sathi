def test_claim_constants():
    from app.services.matching.scorer import (
        WEIGHT_SKILL,
        WEIGHT_LOCATION,
        WEIGHT_AVAILABILITY,
        WEIGHT_RATING,
        WEIGHT_EXPERIENCE,
        WEIGHT_BIO_ECONOMIC,
    )
    from app.config import MAX_FATIGUE_THRESHOLD, settings
    from app.services.matching.equity_graph import (
        WEIGHT_FATIGUE_CAPACITY,
        FATIGUE_SAFE_LOAD,
        FATIGUE_DECAY,
        FATIGUE_WINDOW_DAYS,
        STATUS_MULTIPLIER_ACTIVE,
    )
    from app.services.proof_verification import HAMMING_THRESHOLD
    from app.services.peer_verification import (
        MIN_VOTERS,
        MIN_WEIGHT,
        MIN_SCORE,
    )

    # 1. Scorer weights
    assert WEIGHT_SKILL == 0.30
    assert WEIGHT_LOCATION == 0.20
    assert WEIGHT_AVAILABILITY == 0.20
    assert WEIGHT_RATING == 0.10
    assert WEIGHT_EXPERIENCE == 0.10
    assert WEIGHT_BIO_ECONOMIC == 0.10

    # 2. Fatigue & Proof settings
    assert MAX_FATIGUE_THRESHOLD == 80.0
    assert settings.PROOF_MAX_DISTANCE_M == 500.0
    assert settings.PROOF_NONCE_GRACE_DAYS == 2
    assert settings.PROOF_CODE_MAX_TRIES == 5

    # 3. Equity Graph constants
    assert FATIGUE_SAFE_LOAD == 18.0
    assert FATIGUE_DECAY == 0.8
    assert FATIGUE_WINDOW_DAYS == 7
    assert STATUS_MULTIPLIER_ACTIVE == 0.5
    assert WEIGHT_FATIGUE_CAPACITY == 0.20

    # 4. Proof verification Hamming threshold (16x16 aHash = 256 bits, 64 hex chars)
    assert HAMMING_THRESHOLD == 6

    # 5. Peer verification consensus constants
    assert MIN_VOTERS == 3
    assert MIN_WEIGHT == 3.0
    assert MIN_SCORE == 75.0

    print("All claim constants verified.")
