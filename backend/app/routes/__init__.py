"""
Routes package.

Register all route modules here and import the main router in main.py.
"""
from fastapi import APIRouter

from app.channels.voice import voice_router
from app.channels.whatsapp import whatsapp_router
from app.routes.auth import router as auth_router
from app.routes.bookings import bookings_router
from app.routes.cooperative import router as cooperative_router
from app.routes.equity import equity_router
from app.routes.health import router as health_router
from app.routes.matching import matching_router
from app.routes.service_requests import router as requests_router
from app.routes.services import router as services_router
from app.routes.trust import trust_router
from app.routes.workers import router as workers_router
from app.routes.peer_verification import peer_router
from app.routes.microcredit import router as microcredit_router
from app.routes.governance import router as governance_router

api_router = APIRouter()

api_router.include_router(health_router, prefix="/api")
api_router.include_router(auth_router, prefix="/api")
api_router.include_router(workers_router, prefix="/api")
api_router.include_router(cooperative_router, prefix="/api")
api_router.include_router(services_router, prefix="/api")
api_router.include_router(requests_router, prefix="/api")
api_router.include_router(matching_router, prefix="/api")
api_router.include_router(bookings_router, prefix="/api")
api_router.include_router(equity_router, prefix="/api")
api_router.include_router(trust_router, prefix="/api")
api_router.include_router(peer_router, prefix="/api")
api_router.include_router(microcredit_router, prefix="/api")
api_router.include_router(governance_router, prefix="/api")

from app.routes.india_stack import router as india_stack_router
from app.routes.timebank import router as timebank_router

api_router.include_router(india_stack_router, prefix="/api")
api_router.include_router(timebank_router, prefix="/api")

api_router.include_router(whatsapp_router, prefix="/api")
api_router.include_router(voice_router, prefix="/api")







