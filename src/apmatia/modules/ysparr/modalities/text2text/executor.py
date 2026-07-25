from apmatia.modules.ysparr.core.types import ExecutionResult, PromptRequest


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

    stopped = False

    try:
        for chunk in backend.stream(request):
            if request.stop_event is not None and request.stop_event.is_set():
                stopped = True
                break
            storage.append(request, chunk)
            if request.stop_event is not None and request.stop_event.is_set():
                stopped = True
                break
    finally:
        storage.finalize(request)

    return ExecutionResult(
        prompt_id=request.prompt_id,
        status="stopped" if stopped else "completed",
        output_path=output_path,
    )
