from fastapi import APIRouter

from .agent_routes import router as agent_router
from .agent_prompt_routes import router as agent_prompt_router
from .ai_model_executor_routes import router as ai_model_executor_router
from .ai_host_management_routes import router as ai_host_management_router
from .auth_routes import router as auth_router
from .ai_model_manager_routes import router as ai_model_manager_router
from .discussion_routes import router as discussion_router
from .groups_routes import router as groups_router
from .memory_routes import router as memory_router
from .model_routes import router as model_router
from .module_routes import router as module_router
from .prompt_routes import router as prompt_router
from .settings_routes import router as settings_router
from .tool_routes import router as tool_router
from .users_routes import router as users_router
from .wiki_routes import router as wiki_router

router = APIRouter()
router.include_router(prompt_router)
router.include_router(discussion_router)
router.include_router(settings_router)
router.include_router(users_router)
router.include_router(groups_router)
router.include_router(auth_router)
router.include_router(agent_router)
router.include_router(agent_prompt_router)
router.include_router(ai_model_executor_router)
router.include_router(ai_host_management_router)
router.include_router(ai_model_manager_router)
router.include_router(model_router)
router.include_router(module_router)
router.include_router(memory_router)
router.include_router(tool_router)
router.include_router(wiki_router)
