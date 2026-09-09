from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", summary="Health check")
def health_check():
    """
    Basic health endpoint.
    Returns 200 OK when the backend is running.
    """
    return {"status": "ok"}
