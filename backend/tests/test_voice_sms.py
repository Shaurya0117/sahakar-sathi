"""
Tests for Voice Booking & Hindi SMS Dispatch (Patent Feature: Zero-Screen-Touch).
"""
import pytest
from app.services.sms_service import (
    build_hindi_job_sms,
    build_hindi_confirmation_sms,
    build_hindi_fallback_sms,
    _to_hindi_service,
)


def test_hindi_service_mapping():
    """Verify English services map to appropriate Hindi labels."""
    assert _to_hindi_service("Electrician") == "बिजली का काम"
    assert _to_hindi_service("Plumber") == "नल/पाइप ठीक करना"
    assert _to_hindi_service("AC Repair") == "एसी सर्विस"
    assert _to_hindi_service("Full Home Cleaning") == "घर की सफाई"
    assert _to_hindi_service("Custom Unknown Service") == "Custom Unknown Service"


def test_build_hindi_job_sms():
    """Verify Hindi job SMS contains all required details and choice prompts."""
    sms = build_hindi_job_sms(
        service_name="Electrician",
        customer_name="Priya Sharma",
        location="Sector 62, Noida",
        scheduled_date="2026-11-02",
        scheduled_time="14:00",
        booking_id=101,
    )
    assert "#101" in sms
    assert "बिजली का काम" in sms
    assert "Priya Sharma" in sms
    assert "Sector 62, Noida" in sms
    assert "स्वीकार=1 | मना=2 भेजें" in sms


def test_build_hindi_confirmation_sms():
    """Verify accepted and declined confirmation texts."""
    accepted_msg = build_hindi_confirmation_sms(accepted=True, booking_id=101)
    assert "धन्यवाद" in accepted_msg
    assert "#101" in accepted_msg

    declined_msg = build_hindi_confirmation_sms(accepted=False, booking_id=101)
    assert "ठीक है" in declined_msg
    assert "#101" in declined_msg


def test_build_hindi_fallback_sms():
    """Verify fallback notification text."""
    fallback_msg = build_hindi_fallback_sms(booking_id=101)
    assert "#101" in fallback_msg
    assert "काम" in fallback_msg
