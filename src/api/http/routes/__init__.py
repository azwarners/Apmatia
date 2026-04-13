from fastapi import APIRouter

from .auth_routes import router as auth_router
from .discussion_routes import router as discussion_router
from .groups_routes import router as groups_router
from .prompt_routes import router as prompt_router
from .settings_routes import router as settings_router
from .users_routes import router as users_router

router = APIRouter()
router.include_router(prompt_router)
router.include_router(discussion_router)
router.include_router(settings_router)
router.include_router(users_router)
router.include_router(groups_router)
router.include_router(auth_router)
