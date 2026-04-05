from ysparr.core.types import ExecutionResult, PromptRequest


def execute(request: PromptRequest, backend, storage) -> ExecutionResult:
    """
    Execute a text-to-text request.

    Flow:
    - initialize storage
    - stream output from backend
    - append each chunk to storage
    - finalize storage

    Guarantees:
    - storage.finalize() is always called
    - append is called once per streamed chunk
    """

    output_path = storage.initialize(request)

    try:
        for chunk in backend.stream(request):
            storage.append(request, chunk)
    finally:
        storage.finalize(request)

    return ExecutionResult(
        prompt_id=request.prompt_id,
        status="completed",
        output_path=output_path,
    )
