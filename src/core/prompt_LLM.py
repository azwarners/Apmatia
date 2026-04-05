import json
import uuid

from ysparr.core.types import PromptRequest
from ysparr.modalities.text2text.backends.koboldcpp_backend import KoboldCppBackend


def prompt_llm(prompt: str = "Hello") -> str:
    request = PromptRequest(
        prompt_id=str(uuid.uuid4()),
        prompt_text=f"User: {prompt}\nAssistant:",
        model_name="default",
    )

    import os

    backend = KoboldCppBackend(
        base_url=os.getenv("KOBOLDCPP_URL", "http://localhost:5001")
    )

    raw_chunks = []
    for chunk in backend.stream(request):
        raw_chunks.append(chunk)

    raw_text = "\n".join(raw_chunks).strip()

    try:
        payload = json.loads(raw_text)
        return payload["results"][0]["text"].strip()
    except Exception:
        return raw_text
