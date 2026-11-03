"""
SMS Service — Sahakar Sathi Voice Dispatch System.

Supports two backends controlled by SMS_GATEWAY config:
  - "textbelt"  : Textbelt free tier (1 SMS/day for demo)
  - "android"   : Android SMS Gateway (production, self-hosted)

Patent Feature: Zero-Screen-Touch Voice Booking — the customer says what they need,
the backend dispatches a Hindi SMS to the matched worker's basic phone automatically.
"""
import json
import logging
from typing import Optional
import urllib.parse
import urllib.request

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

from app.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Hindi SMS Templates
# ---------------------------------------------------------------------------

SERVICE_HINDI_MAP = {
    "electrician":    "बिजली का काम",
    "plumber":        "नल/पाइप ठीक करना",
    "cleaner":        "सफाई का काम",
    "carpenter":      "बढ़ई का काम",
    "ac repair":      "एसी सर्विस",
    "ac servicing":   "एसी सर्विस",
    "painter":        "रंग-पेंट का काम",
    "painting":       "रंग-पेंट का काम",
    "pest control":   "कीट-नाशक सेवा",
    "appliance repair": "उपकरण मरम्मत",
    "home cleaning":  "घर की सफाई",
    "deep cleaning":  "गहरी सफाई",
}


def _to_hindi_service(service_name: str) -> str:
    """Convert English service name to Hindi label for SMS."""
    key = service_name.lower().strip()
    for eng, hindi in SERVICE_HINDI_MAP.items():
        if eng in key:
            return hindi
    return service_name  # fallback: send as-is


def build_hindi_job_sms(
    service_name: str,
    customer_name: str,
    location: str,
    scheduled_date: str,
    scheduled_time: str,
    booking_id: int,
) -> str:
    """
    Build a Hindi Devanagari SMS message to send to the assigned worker.

    Keeps message under 160 chars (1 SMS unit) where possible.
    """
    hindi_service = _to_hindi_service(service_name)
    cust_clean = (customer_name or "ग्राहक").strip()[:15]
    loc_clean = (location or "").strip()[:25]
    msg = (
        f"नया काम! #{booking_id}\n"
        f"सेवा: {hindi_service}\n"
        f"ग्राहक: {cust_clean}\n"
        f"पता: {loc_clean}\n"
        f"समय: {scheduled_date} {scheduled_time}\n"
        f"स्वीकार=1 | मना=2 भेजें"
    )
    return msg


def build_hindi_confirmation_sms(accepted: bool, booking_id: int) -> str:
    """Hindi SMS sent back to worker after their reply is processed."""
    if accepted:
        return (
            f"धन्यवाद! काम #{booking_id} आपको मिल गया। "
            f"समय पर पहुंचें। ग्राहक का इंतज़ार है।"
        )
    return (
        f"ठीक है। काम #{booking_id} किसी और को दिया जाएगा। "
        f"अगली बार जरूर लें!"
    )


def build_hindi_fallback_sms(booking_id: int) -> str:
    """Hindi SMS sent to worker when booking is reassigned away from them."""
    return (
        f"काम #{booking_id} के लिए कोई और मिल गया। "
        f"अगली बार तेज़ी से जवाब दें!"
    )


# ---------------------------------------------------------------------------
# SMS Backend Implementations
# ---------------------------------------------------------------------------

def _send_via_textbelt(phone: str, message: str) -> dict:
    """
    Send SMS via Textbelt.

    Free key: "textbelt" — 1 SMS/day globally.
    Paid key: purchase from textbelt.com for real quota.

    phone must be E.164 format: +919XXXXXXXXX
    """
    key = getattr(settings, "TEXTBELT_KEY", "textbelt")
    payload = {
        "phone": phone,
        "message": message,
        "key": key,
    }

    try:
        if HAS_HTTPX:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post("https://textbelt.com/text", data=payload)
                data = resp.json()
        else:
            encoded_data = urllib.parse.urlencode(payload).encode("utf-8")
            req = urllib.request.Request("https://textbelt.com/text", data=encoded_data, method="POST")
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

        if data.get("success"):
            logger.info("Textbelt SMS sent to %s (textId=%s, quota=%s)",
                        phone[-4:], data.get("textId"), data.get("quotaRemaining"))
        else:
            logger.warning("Textbelt SMS failed: %s", data.get("error"))
        return data
    except Exception as exc:
        logger.error("Textbelt request error: %s", exc)
        return {"success": False, "error": str(exc)}


def _send_via_android_gateway(phone: str, message: str) -> dict:
    """
    Send SMS via Android SMS Gateway (self-hosted on spare Android phone).

    Set ANDROID_GW_URL, ANDROID_GW_USER, ANDROID_GW_PASS in .env
    Docs: https://android-sms-gateway.com/docs/api/
    """
    gw_url = getattr(settings, "ANDROID_GW_URL", "")
    gw_user = getattr(settings, "ANDROID_GW_USER", "")
    gw_pass = getattr(settings, "ANDROID_GW_PASS", "")

    if not gw_url:
        logger.error("ANDROID_GW_URL not configured — cannot send SMS")
        return {"success": False, "error": "Android gateway URL not set"}

    payload = {"message": message, "phoneNumbers": [phone]}

    try:
        if HAS_HTTPX:
            auth = (gw_user, gw_pass) if gw_user else None
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    f"{gw_url.rstrip('/')}/message",
                    json=payload,
                    auth=auth,
                )
                data = resp.json() if resp.content else {}
                success = resp.status_code == 202
        else:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{gw_url.rstrip('/')}/message",
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            if gw_user:
                import base64
                auth_str = f"{gw_user}:{gw_pass}"
                b64_auth = base64.b64encode(auth_str.encode()).decode()
                req.add_header("Authorization", f"Basic {b64_auth}")
            with urllib.request.urlopen(req, timeout=10) as response:
                success = response.status == 202
                data = json.loads(response.read().decode("utf-8"))

        if success:
            logger.info("Android Gateway SMS sent to %s", phone[-4:])
        else:
            logger.warning("Android Gateway SMS failed: %s", data)
        return {"success": success, "data": data}
    except Exception as exc:
        logger.error("Android Gateway request error: %s", exc)
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def send_sms(phone: str, message: str) -> dict:
    """
    Dispatch an SMS to the given phone number.

    Automatically routes to the correct backend based on SMS_GATEWAY config:
      - "textbelt"  → Textbelt API (demo / free tier)
      - "android"   → Android SMS Gateway (production)

    Returns a dict with at least {"success": bool}.
    """
    gateway = getattr(settings, "SMS_GATEWAY", "textbelt")

    # Normalize phone: ensure E.164 for Indian numbers
    if phone and not phone.startswith("+"):
        if phone.startswith("0"):
            phone = "+91" + phone[1:]
        elif len(phone) == 10:
            phone = "+91" + phone

    if gateway == "android":
        return _send_via_android_gateway(phone, message)
    else:
        # Default to textbelt (safe fallback)
        return _send_via_textbelt(phone, message)
