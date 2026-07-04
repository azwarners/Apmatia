from .actions import ACTION_DESCRIPTORS
from .commands import COMMAND_DESCRIPTORS
from .collections import AI_MODEL_COLLECTION_VIEW_SPECS
from .models import GGUFModelRecord, TaskSizePreference
from .module import APMATIA_AI_MODEL_MANAGER_MODULE, register
from .module_views import ApmatiaAiModelManagerModuleViewProvider
from .services import AIModelManager, estimate_ram_bytes, estimate_vram_bytes, infer_size_class
from .views import VIEW_DESCRIPTORS

__all__ = [
    "ACTION_DESCRIPTORS",
    "AIModelManager",
    "AI_MODEL_COLLECTION_VIEW_SPECS",
    "APMATIA_AI_MODEL_MANAGER_MODULE",
    "ApmatiaAiModelManagerModuleViewProvider",
    "COMMAND_DESCRIPTORS",
    "GGUFModelRecord",
    "TaskSizePreference",
    "estimate_ram_bytes",
    "estimate_vram_bytes",
    "VIEW_DESCRIPTORS",
    "infer_size_class",
    "register",
]
