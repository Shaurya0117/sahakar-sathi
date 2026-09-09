"""
WhatsApp Webhook Request Payload Parser.

Parses Telnyx JSON payloads, Twilio form-encoded payloads, and standard Mock JSON payloads.
Extracts phone number, message body, latitude/longitude coordinates, and provider event ID.
"""
import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


def parse_whatsapp_payload(
    data: Dict[str, Any]
) -> Tuple[str, Optional[str], Optional[float], Optional[float], Optional[str]]:
    """
    Extract (phone, message_text, latitude, longitude, event_id) from incoming payload.

    Supports:
    1. Telnyx v2 JSON webhook structure (data -> payload -> from -> phone_number / location / text)
    2. Twilio form-urlencoded / JSON structure (From -> whatsapp:+..., Body, Latitude, Longitude, MessageSid)
    3. Mock / Test JSON structure (phone, message, latitude, longitude, event_id)
    """
    phone: str = ""
    body: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    event_id: Optional[str] = None

    if not isinstance(data, dict):
        return "", None, None, None, None

    # Check for Telnyx v2 Webhook envelope format ("data" wrapper)
    telnyx_data = data.get("data")
    if isinstance(telnyx_data, dict):
        event_id = telnyx_data.get("id")
        telnyx_payload = telnyx_data.get("payload", {})
        if isinstance(telnyx_payload, dict):
            if not event_id:
                event_id = telnyx_payload.get("id")

            # Extract Phone
            from_obj = telnyx_payload.get("from")
            if isinstance(from_obj, dict):
                phone = from_obj.get("phone_number") or ""
            elif isinstance(from_obj, str):
                phone = from_obj

            # Extract Text
            body = telnyx_payload.get("text") or telnyx_payload.get("body")

            # Extract Telnyx Location payload
            loc_obj = telnyx_payload.get("location")
            if isinstance(loc_obj, dict):
                try:
                    lat = float(loc_obj.get("latitude"))
                    lng = float(loc_obj.get("longitude"))
                except (ValueError, TypeError):
                    pass
                
                # If text message is empty or generic, use location address/name
                loc_address = loc_obj.get("address") or loc_obj.get("name")
                if not body and loc_address:
                    body = f"Location drop: {loc_address}"

    # Fallback to direct / flat payload structure (Twilio / Mock / Direct Telnyx payload)
    if not phone:
        # Extract Phone
        raw_phone = (
            data.get("From")
            or data.get("phone")
            or data.get("sender")
            or data.get("from")
            or ""
        )
        if isinstance(raw_phone, dict):
            phone = raw_phone.get("phone_number") or ""
        else:
            phone = str(raw_phone)

        # Extract Text
        body = data.get("Body") or data.get("message") or data.get("text") or body

        # Extract Event ID
        event_id = data.get("MessageSid") or data.get("id") or data.get("event_id")

    # Clean WhatsApp prefix if present (e.g. "whatsapp:+919876500000" -> "+919876500000")
    if phone.startswith("whatsapp:"):
        phone = phone.replace("whatsapp:", "")
    phone = phone.strip()

    # Extract Location coordinates if not already populated
    if lat is None or lng is None:
        if "Latitude" in data and "Longitude" in data:
            try:
                lat = float(data["Latitude"])
                lng = float(data["Longitude"])
            except (ValueError, TypeError):
                pass
        elif "latitude" in data and "longitude" in data:
            try:
                lat = float(data["latitude"])
                lng = float(data["longitude"])
            except (ValueError, TypeError):
                pass

    return phone, body, lat, lng, event_id
