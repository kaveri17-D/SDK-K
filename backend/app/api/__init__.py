from fastapi import APIRouter
from backend.app.api.nodes import router as nodes_router
from backend.app.api.network import router as network_router
from backend.app.api.health import router as health_router
from backend.app.api.enrollment import router as enrollment_router
from backend.app.api.dashboard import router as dashboard_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(nodes_router)
api_router.include_router(network_router)
api_router.include_router(enrollment_router)
api_router.include_router(dashboard_router)

__all__ = ["api_router"]
