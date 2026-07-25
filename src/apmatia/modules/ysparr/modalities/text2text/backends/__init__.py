"""Text2Text backends."""

from apmatia.modules.ysparr.modalities.text2text.backends.koboldcpp_backend import KoboldCppBackend
from apmatia.modules.ysparr.modalities.text2text.backends.openai_compatible_backend import (
    OpenAICompatibleBackend,
)

__all__ = ["KoboldCppBackend", "OpenAICompatibleBackend"]
