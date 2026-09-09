"""
Deterministic Conversation State Machine and Parsing Utilities.

Handles multi-channel service booking flows (WhatsApp & Voice/IVR).
"""
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.conversation_session import ConversationSession
from app.models.service import Service
from app.models.user import User, UserRole
from app.services.service_request import create_service_request


def normalize_phone(phone: str) -> str:
    """Normalize phone number by stripping whitespace, dashes, and extra formatting."""
    cleaned = re.sub(r"[^\d+]", "", phone.strip())
    return cleaned


def find_customer_by_phone(db: Session, raw_phone: str) -> Optional[User]:
    """
    Locate a CUSTOMER user account linked to the provided phone number.
    Supports exact string match, +91 prefixed match, or last 10 digits match.
    """
    normalized = normalize_phone(raw_phone)
    digits_only = re.sub(r"\D", "", normalized)

    # 1. Exact match
    user = db.query(User).filter(User.phone == normalized, User.role == UserRole.CUSTOMER).first()
    if user:
        return user

    if len(digits_only) >= 10:
        last10 = digits_only[-10:]
        # Query candidates
        customers = db.query(User).filter(User.role == UserRole.CUSTOMER).all()
        for c in customers:
            if c.phone:
                c_digits = re.sub(r"\D", "", c.phone)
                if len(c_digits) >= 10 and c_digits[-10:] == last10:
                    return c

    return None


def parse_date_input(text: str) -> str:
    """
    Normalize human date inputs like 'today', 'tomorrow', '27 Aug', '2026-08-27'
    into standard ISO date format YYYY-MM-DD.
    """
    text_clean = text.strip().lower()
    today = datetime.now().date()

    if text_clean in ("today", "now"):
        return today.isoformat()
    if text_clean in ("tomorrow", "tomm", "tmrw"):
        return (today + timedelta(days=1)).isoformat()
    if text_clean in ("day after tomorrow", "day after"):
        return (today + timedelta(days=2)).isoformat()

    # Try parsing YYYY-MM-DD
    try:
        dt = datetime.strptime(text_clean, "%Y-%m-%d")
        return dt.date().isoformat()
    except ValueError:
        pass

    # Try parsing DD/MM/YYYY or DD-MM-YYYY
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d %B %Y", "%d %b", "%d %B"):
        try:
            dt = datetime.strptime(text_clean, fmt)
            # If year missing, assume current or next year
            if dt.year == 1900:
                dt = dt.replace(year=today.year)
                if dt.date() < today:
                    dt = dt.replace(year=today.year + 1)
            return dt.date().isoformat()
        except ValueError:
            pass

    # Default fallback: keep cleaned text or current date + 1 day
    return (today + timedelta(days=1)).isoformat()


def parse_time_input(text: str) -> str:
    """
    Normalize human time inputs like '2 PM', '14:00', 'morning', 'afternoon'
    into standard HH:MM format.
    """
    text_clean = text.strip().lower()

    if "morning" in text_clean:
        return "10:00"
    if "afternoon" in text_clean:
        return "14:00"
    if "evening" in text_clean:
        return "17:00"

    # Match 2 PM, 2:30 PM, 14:00
    m12 = re.search(r"^(\d{1,2})(?::(\d{2}))?\s*(am|pm)$", text_clean)
    if m12:
        hr = int(m12.group(1))
        mn = int(m12.group(2)) if m12.group(2) else 0
        ampm = m12.group(3)
        if ampm == "pm" and hr < 12:
            hr += 12
        elif ampm == "am" and hr == 12:
            hr = 0
        return f"{hr:02d}:{mn:02d}"

    m24 = re.search(r"^(\d{1,2})(?::(\d{2}))?$", text_clean)
    if m24:
        hr = int(m24.group(1))
        mn = int(m24.group(2)) if m24.group(2) else 0
        if 0 <= hr <= 23 and 0 <= mn <= 59:
            return f"{hr:02d}:{mn:02d}"

    return "10:00"


def get_active_services_menu(db: Session) -> Tuple[str, Dict[int, Service]]:
    """Fetch active services and build numbered string menu."""
    services = db.query(Service).filter(Service.is_active == True).order_by(Service.id).all()
    menu_lines = []
    service_map = {}
    for idx, s in enumerate(services, 1):
        service_map[idx] = s
        menu_lines.append(f"{idx}. {s.name}")

    menu_str = "\n".join(menu_lines)
    return menu_str, service_map


def process_channel_message(
    db: Session,
    channel: str,
    raw_phone: str,
    message_text: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
) -> Tuple[str, str]:
    """
    Process an incoming message or payload from any channel (WhatsApp, Voice, Test).

    Returns:
        (reply_message, current_state)
    """
    # 1. Identify customer
    customer = find_customer_by_phone(db, raw_phone)
    if not customer:
        normalized_phone = normalize_phone(raw_phone)
        reply = (
            f"Welcome to Sahakar Sathi!\n\n"
            f"We could not find a registered customer account linked to phone number {normalized_phone}.\n\n"
            f"To request household & community services via WhatsApp or Phone, please register or link your mobile number at our official portal:\n"
            f"http://localhost:5173"
        )
        return reply, "UNAUTHORIZED"

    # 2. Fetch or create session
    session = (
        db.query(ConversationSession)
        .filter(
            ConversationSession.channel == channel,
            ConversationSession.phone == customer.phone,
        )
        .first()
    )

    if not session:
        session = ConversationSession(
            channel=channel,
            phone=customer.phone,
            customer_id=customer.id,
            state="NEW",
            context_data={},
        )
        db.add(session)
        db.commit()
        db.refresh(session)
    else:
        # Update customer_id if missing
        if session.customer_id != customer.id:
            session.customer_id = customer.id
            db.commit()

    text_input = (message_text or "").strip()
    text_lower = text_input.lower()

    # Reset / Cancel logic
    if text_lower in ("cancel", "exit"):
        session.state = "CANCELLED"
        session.context_data = {}
        db.commit()
        return (
            "Your service request conversation has been cancelled.\n"
            "Reply 'Hi' or 'Start' anytime to begin a new service request.",
            "CANCELLED",
        )

    if session.state in ("NEW", "CANCELLED", "REQUEST_CREATED") or text_lower in (
        "hi",
        "hello",
        "start",
        "reset",
        "menu",
    ):
        session.state = "SELECT_SERVICE"
        session.context_data = {}
        db.commit()

        menu_str, _ = get_active_services_menu(db)
        reply = (
            f"Hello {customer.name}! Welcome to Sahakar Sathi (Cooperative Community Services).\n"
            f"How can we help you today?\n\n"
            f"Please reply with the number of your required service:\n"
            f"{menu_str}\n\n"
            f"Reply 'cancel' at any step to stop."
        )
        return reply, "SELECT_SERVICE"

    ctx = dict(session.context_data or {})

    # State Machine Handling
    if session.state == "SELECT_SERVICE":
        menu_str, service_map = get_active_services_menu(db)
        selected_service = None

        # Check numeric selection
        if text_input.isdigit():
            idx = int(text_input)
            if idx in service_map:
                selected_service = service_map[idx]
        else:
            # Match by name or partial text
            services = list(service_map.values())
            for s in services:
                if text_lower in s.name.lower() or text_lower in s.category.lower():
                    selected_service = s
                    break

        if not selected_service:
            reply = (
                f"Invalid selection. Please choose a valid service number from the menu:\n\n"
                f"{menu_str}\n\n"
                f"Reply 'cancel' to exit."
            )
            return reply, "SELECT_SERVICE"

        ctx["service_id"] = selected_service.id
        ctx["service_name"] = selected_service.name
        session.context_data = ctx
        session.state = "DESCRIPTION"
        db.commit()

        reply = (
            f"You selected: *{selected_service.name}*.\n\n"
            f"Please briefly describe the problem or task required (e.g. 'Ceiling fan is making noise')."
        )
        return reply, "DESCRIPTION"

    elif session.state == "DESCRIPTION":
        if len(text_input) < 3:
            return (
                "Please provide a slightly more descriptive summary of the task required.",
                "DESCRIPTION",
            )

        ctx["description"] = text_input
        session.context_data = ctx
        session.state = "LOCATION"
        db.commit()

        reply = (
            f"Got it!\n\n"
            f"Please share your service location.\n"
            f"You can send a WhatsApp Location 📍 drop or type your street/area address (e.g. 'Sector 62, Noida')."
        )
        return reply, "LOCATION"

    elif session.state == "LOCATION":
        # Check if coordinates provided
        if latitude is not None and longitude is not None:
            ctx["latitude"] = float(latitude)
            ctx["longitude"] = float(longitude)
            loc_str = text_input if text_input else f"GPS ({latitude:.4f}, {longitude:.4f})"
            ctx["location"] = loc_str
        elif len(text_input) >= 3:
            ctx["location"] = text_input
            if latitude is not None:
                ctx["latitude"] = float(latitude)
            if longitude is not None:
                ctx["longitude"] = float(longitude)
        else:
            return (
                "Please provide a valid location address or share your location drop.",
                "LOCATION",
            )

        session.context_data = ctx
        session.state = "DATE"
        db.commit()

        reply = (
            f"Location set to: *{ctx['location']}*.\n\n"
            f"What date would you prefer for the service?\n"
            f"(e.g. 'Tomorrow', '27 Aug', or 'YYYY-MM-DD')."
        )
        return reply, "DATE"

    elif session.state == "DATE":
        parsed_date = parse_date_input(text_input)
        ctx["preferred_date"] = parsed_date
        session.context_data = ctx
        session.state = "TIME"
        db.commit()

        reply = (
            f"Preferred date set to: *{parsed_date}*.\n\n"
            f"What time would you prefer?\n"
            f"(e.g. '2 PM', '14:00', or 'Morning')."
        )
        return reply, "TIME"

    elif session.state == "TIME":
        parsed_time = parse_time_input(text_input)
        ctx["preferred_time"] = parsed_time
        session.context_data = ctx
        session.state = "CONFIRMATION"
        db.commit()

        reply = (
            f"Please confirm your service request details:\n\n"
            f"📋 *Service:* {ctx.get('service_name')}\n"
            f"📝 *Description:* {ctx.get('description')}\n"
            f"📍 *Location:* {ctx.get('location')}\n"
            f"📅 *Date:* {ctx.get('preferred_date')}\n"
            f"⏰ *Time:* {ctx.get('preferred_time')}\n\n"
            f"Reply:\n"
            f"1. Confirm & Submit\n"
            f"2. Cancel"
        )
        return reply, "CONFIRMATION"

    elif session.state == "CONFIRMATION":
        if text_lower in ("1", "confirm", "yes", "submit", "ok"):
            # Create ServiceRequest using existing service logic
            from app.schemas.service_request import ServiceRequestCreateRequest

            req_schema = ServiceRequestCreateRequest(
                service_id=ctx["service_id"],
                description=ctx["description"],
                location=ctx["location"],
                latitude=ctx.get("latitude"),
                longitude=ctx.get("longitude"),
                preferred_date=ctx["preferred_date"],
                preferred_time=ctx["preferred_time"],
            )

            request_obj = create_service_request(db, customer.id, req_schema)

            session.state = "REQUEST_CREATED"
            session.context_data["created_request_id"] = request_obj.id
            db.commit()

            reply = (
                f"✅ *Your service request has been submitted successfully!*\n\n"
                f"Request ID: *#{request_obj.id}*\n"
                f"Status: *PENDING Allocation*\n\n"
                f"Service: {ctx.get('service_name')}\n"
                f"Location: {ctx.get('location')}\n"
                f"Date: {ctx.get('preferred_date')}\n"
                f"Time: {ctx.get('preferred_time')}\n\n"
                f"A cooperative administrator will evaluate worker recommendations and allocate a verified worker shortly. "
                f"You can track this request anytime on your Sahakar Sathi portal account."
            )
            return reply, "REQUEST_CREATED"
        elif text_lower in ("2", "no", "cancel"):
            session.state = "CANCELLED"
            session.context_data = {}
            db.commit()
            return (
                "Service request booking cancelled. Reply 'Hi' or 'Start' to begin a new request.",
                "CANCELLED",
            )
        else:
            reply = (
                f"Invalid option. Please reply '1' to Confirm & Submit or '2' to Cancel."
            )
            return reply, "CONFIRMATION"

    # Default fallback
    session.state = "SELECT_SERVICE"
    session.context_data = {}
    db.commit()
    menu_str, _ = get_active_services_menu(db)
    return f"Reply with service number:\n{menu_str}", "SELECT_SERVICE"
