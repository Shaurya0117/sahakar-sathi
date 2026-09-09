# Sahakar Sathi — Smart India Hackathon 2026 🇮🇳

![Sahakar Sathi](https://img.shields.io/badge/SIH-2026-orange?style=for-the-badge) ![Status](https://img.shields.io/badge/Status-Completed-success?style=for-the-badge) ![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)

**Sahakar Sathi** is a cooperative-owned digital gig marketplace that directly connects households and local communities with verified, background-checked service professionals (electricians, plumbers, cleaners, carpenters, etc.). 

Built specifically for the **Smart India Hackathon 2026**, this platform acts as an official, transparent public service portal. It is designed to replace predatory commission-based gig platforms (like Urban Company or TaskRabbit) with a fair, equitable, worker-governed cooperative model. 

### 🎯 The Problem
Gig workers currently face exorbitant commission fees (often up to 25-30%), algorithmic biases that unfairly distribute work, and lack of true ownership. Customers lack a unified, official, trust-verified portal for community services.

### 💡 Our Solution
Sahakar Sathi ensures **0% predatory platform fees** (direct peer-to-peer payment), worker credential verification by cooperative admins, and a smart **Equitable Workload Recommendation Engine** that distributes jobs fairly among cooperative members based on distance, skill, and recent workload.

---

## Key Platform Features

- **Official Service Marketplace:** Clean, accessible portal for browsing cooperative service categories (Electrical Repairs, Plumbing, Cleaning, Carpentry, Painting, AC Servicing).
- **Multi-Channel Service Booking:** Customers can request services via Website, WhatsApp, or Phone/IVR. All channels feed into the exact same central `ServiceRequest` entity and cooperative allocation workflow.
- **Service Request Management:** Request creation with optional browser-assisted geolocation ("📍 Use My Current Location"), WhatsApp location drop, or manual locality entry.
- **Worker Recommendations:** Transparent recommendation allocation considering worker skills, Haversine location distance, availability, experience, and current workload.
- **Worker Workspace:** Member worker dashboard for managing availability, viewing allocated jobs, and updating job execution status (`ACCEPTED`, `IN_PROGRESS`, `COMPLETED`).
- **Cooperative Administration:** Management portal for cooperative administrators to inspect worker credentials, verify members, and allocate service requests.
- **Location Privacy:** Exact worker coordinates are kept private and never exposed to customers. Only human-readable service areas (e.g., *"Sector 62, Noida"*) are displayed.

---

## Service Request Channels (Web, WhatsApp, Phone)

Sahakar Sathi provides 3 access channels feeding into a single, unified backend workflow:

| Channel | Interface | How It Works | Status |
| :--- | :--- | :--- | :--- |
| **1. Web Portal** | Online Form (`/customer`) | Full interactive web catalog, GPS picker, date/time scheduling | **IMPLEMENTED** |
| **2. WhatsApp** | Text / Location Messages | Deterministic state machine (`SELECT_SERVICE` $\rightarrow$ `DESCRIPTION` $\rightarrow$ `LOCATION` $\rightarrow$ `DATE` $\rightarrow$ `TIME` $\rightarrow$ `CONFIRMATION`) | **IMPLEMENTED** (Mock, Telnyx, Twilio) |
| **3. Phone / IVR** | Keypad DTMF / Speech | Automated helpline IVR prompt system mapping keypresses to service requests | **IMPLEMENTED** (Mock & Twilio Ready) |

```
CUSTOMER
  ↓
WhatsApp Message / Location Drop
  ↓
Telnyx WhatsApp Gateway (v2 REST API)
  ↓
Sahakar Sathi Webhook (`POST /api/channels/whatsapp/webhook`)
  ↓
Payload Parser & Security Signature Verification
  ↓
Common Channel Conversation Service (`app/services/channel_booking.py`)
  ↓
ServiceRequest Entity (Status: PENDING)
  ↓
Cooperative Worker Recommendation Engine
  ↓
Admin Allocation
  ↓
Worker Booking & Job Execution
```

---

## Developer / Provider Configuration

Set provider mode in `backend/.env`:
```env
WHATSAPP_PROVIDER=telnyx   # Options: "mock" | "telnyx" | "twilio"
VOICE_PROVIDER=mock      # Options: "mock" | "twilio"

# Telnyx WhatsApp Credentials (required when WHATSAPP_PROVIDER=telnyx)
TELNYX_API_KEY=KEY0123456789...
TELNYX_WHATSAPP_NUMBER=+18001234567
TELNYX_MESSAGING_PROFILE_ID=3fa85f64-5717-4562-b3fc-2c963f66afa6
TELNYX_WEBHOOK_SECRET=

# Optional Twilio Credentials
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
TWILIO_VOICE_NUMBER=+14155238886
```

### Setting Up Telnyx WhatsApp Inbound & Outbound

1. **Telnyx Portal Setup:**
   - Log into [Telnyx Portal](https://portal.telnyx.com/).
   - Navigate to **Messaging** $\rightarrow$ **Messaging Profiles** $\rightarrow$ Create a profile.
   - Attach your WhatsApp Business Account (WABA) or WhatsApp number to the Messaging Profile.
   - Set the Inbound Webhook URL to your public server endpoint:
     `https://<your-domain-or-ngrok>/api/channels/whatsapp/webhook`
   - Set Webhook API Version to `v2` and Failover URL (optional).

2. **Local Testing via HTTPS Tunnel (e.g. ngrok):**
   - Start backend server: `venv\Scripts\uvicorn app.main:app --port 8000`
   - Expose backend via ngrok: `ngrok http 8000`
   - Copy the HTTPS URL (e.g. `https://a1b2c3d4.ngrok-free.app`) into your Telnyx Messaging Profile Inbound Webhook:
     `https://a1b2c3d4.ngrok-free.app/api/channels/whatsapp/webhook`

3. **Real WhatsApp User Booking Test:**
   - Send a WhatsApp message `"Hi"` from a registered customer phone number (e.g., Asha Sharma `+91 98765 00000`) to your Telnyx WhatsApp Number (`+1 800 123 4567`).
   - Sahakar Sathi will reply back on WhatsApp with the active service catalog menu.
   - Reply `"1"` (Plumbing), send problem description, location (or drop GPS location), preferred date, time, and confirm with `"1"`.
   - A `ServiceRequest` is automatically created in the database and appears on the Sahakar Sathi Admin Dashboard for worker allocation.

---

## User Roles & Portal Access

| Role | Portal Capabilities |
| :--- | :--- |
| **Customer** | Browse service catalog, request services with location/schedule, track request status, view assigned cooperative member |
| **Worker** | Maintain profile, set availability, inspect assigned jobs, update status (`Accept`, `Start Service`, `Complete`) |
| **Cooperative Admin** | Overview statistics, manage worker verification, review request allocation recommendations, assign workers |

---

## Member Demo Credentials

| Role | Demo Email / Phone | Password |
| :--- | :--- | :--- |
| **Cooperative Admin** | `admin@sahakarsathi.demo` | `Admin@1234` |
| **Customer (Asha Sharma)** | `asha.customer@sahakarsathi.demo` (`+91 98765 00000`) | `Customer@1234` |
| **Worker (Rahul Kumar)** | `rahul.electrician@sahakarsathi.demo` (`+91 98765 43210`) | `Worker@1234` |

---

## Developer / Provider Configuration

Set provider mode in `.env`:
```env
WHATSAPP_PROVIDER=mock   # "mock" for offline local testing or "twilio"
VOICE_PROVIDER=mock      # "mock" for offline local testing or "twilio"

# Optional Twilio Credentials
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
TWILIO_VOICE_NUMBER=+14155238886
```

### Mock Endpoints for Development & Testing:
- **WhatsApp Simulation:** `POST /api/channels/whatsapp/test-message`
  ```json
  { "phone": "+919876500000", "message": "1" }
  ```
- **Voice Simulation:** `POST /api/channels/voice/test-input`
  ```json
  { "phone": "+919876500000", "digits": "1" }
  ```

---

## Cooperative Governance & Workload Fairness

Sahakar Sathi prioritizes equitable work distribution among qualified member workers. The recommendation engine evaluates:
- **Skill Match (30%)**: Domain relevance and specialized skill qualification.
- **Geographic Proximity (20%)**: Haversine distance brackets (0–2 km = 100, 2–5 km = 90, 5–10 km = 75, 10–20 km = 55, 20+ km = 30) or locality string matching.
- **Availability (20%)**: Active availability declaration.
- **Customer Rating (10%)**: Average rating with neutral entry score for new members.
- **Field Experience (10%)**: Experience years in trade.
- **Workload Fairness (10%)**: $\max(30, 100 - (\text{total\_jobs} \cdot 2.5))$ — provides members with fewer recent jobs a competitive allocation boost.
