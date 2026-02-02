from fastapi import APIRouter
from app.auth.auth_routes import router as auth_router

router = APIRouter()

# Include authentication routes
router.include_router(auth_router)

@router.get("/status")
async def get_status():
    return {"status": "API is running", "service": "Universal RAG Platform"}