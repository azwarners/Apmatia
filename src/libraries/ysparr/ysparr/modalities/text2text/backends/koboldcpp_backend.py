import requests

from ysparr.core.config import get_config_value
from ysparr.core.exceptions import ExecutionError
from ysparr.core.types import PromptRequest


class KoboldCppBackend:
    """
    Backend adapter for KoboldCpp.
    """

    def __init__(self, base_url: str | None = None):
        """
        Args:
            base_url: Optional override
        """

        self.base_url = (
            base_url
            or get_config_value("text2text", "koboldcpp", "base_url")
        )

        if not self.base_url:
            raise ExecutionError(
                "KoboldCpp base_url not provided and not found in config"
            )

        self.base_url = self.base_url.rstrip("/")

    def stream(self, request: PromptRequest):
        url = f"{self.base_url}/api/v1/generate"

        payload = {
            "prompt": request.prompt_text,
            "max_length": 512,
            "temperature": 0.7,
            "stream": True,
        }

        try:
            with requests.post(url, json=payload, stream=True) as response:
                response.raise_for_status()

                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        continue

                    yield line

        except requests.RequestException as error:
            raise ExecutionError("KoboldCpp request failed") from error
