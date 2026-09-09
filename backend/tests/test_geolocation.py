"""
Tests for Geolocation & Distance Scoring Features.
"""
import pytest
from pydantic import ValidationError

from app.schemas.worker import WorkerCreateRequest, WorkerUpdateRequest
from app.schemas.service_request import ServiceRequestCreateRequest
from app.services.matching.scorer import (
    calculate_haversine_distance,
    calculate_location_score,
)


def test_haversine_distance_calculation():
    # Sector 62 Noida to Sector 63 Noida (~1.8 km)
    lat1, lon1 = 28.6280, 77.3649
    lat2, lon2 = 28.6270, 77.3780
    dist = calculate_haversine_distance(lat1, lon1, lat2, lon2)
    assert 1.0 <= dist <= 2.5


def test_location_score_distance_brackets():
    # 0-2 km -> 100 score
    lat1, lon1 = 28.6280, 77.3649
    lat2, lon2 = 28.6281, 77.3650
    score_close = calculate_location_score("Area A", "Area B", lat1, lon1, lat2, lon2)
    assert score_close == 100.0

    # ~15 km (Sector 62 Noida to Connaught Place Delhi) -> 55 score
    lat_cp, lon_cp = 28.6315, 77.2167
    score_far = calculate_location_score("Noida", "Delhi", lat1, lon1, lat_cp, lon_cp)
    assert score_far == 55.0


def test_location_score_fallback_to_string():
    # Missing coordinates -> string fallback
    score_exact = calculate_location_score("Sector 62 Noida", "Sector 62 Noida")
    assert score_exact == 100.0

    score_same_area = calculate_location_score("Sector 62 Noida", "Sector 63 Noida")
    assert score_same_area == 90.0

    score_diff_city = calculate_location_score("Sector 62 Noida", "Vasant Kunj Delhi")
    assert score_diff_city == 40.0


def test_coordinate_pydantic_validations():
    # Valid coordinates
    req = ServiceRequestCreateRequest(
        service_id=1,
        location="Sector 62 Noida",
        latitude=28.6280,
        longitude=77.3649,
        preferred_date="2026-08-26",
        preferred_time="10:00 AM",
        description="Fix fan wiring issue",
    )
    assert req.latitude == 28.6280

    # Invalid latitude (> 90)
    with pytest.raises(ValidationError):
        ServiceRequestCreateRequest(
            service_id=1,
            location="Sector 62 Noida",
            latitude=95.0,
            longitude=77.3649,
            preferred_date="2026-08-26",
            preferred_time="10:00 AM",
            description="Fix fan wiring issue",
        )

    # Invalid longitude (< -180)
    with pytest.raises(ValidationError):
        WorkerCreateRequest(
            profession="Electrician",
            skills=["Wiring"],
            experience_years=5,
            location="Sector 62 Noida",
            latitude=28.6280,
            longitude=-190.0,
        )
