from __future__ import annotations

from pathlib import Path
from typing import Optional

from ysparr.core.exceptions import StorageError
from ysparr.core.types import PromptRequest


class TextFileStorage:
    """
    Persistence layer for text2text output.

    Responsibilities:
    - create output files
    - append streamed text
    - finalize output
    - enforce simple retention policies
    """

    def __init__(
        self,
        output_dir: str,
        *,
        max_files: Optional[int] = None,
    ) -> None:
        """
        Initialize storage.

        Args:
            output_dir: Directory where output files are written
            max_files: Optional global cap on number of stored files
        """
        self.output_dir = Path(output_dir)
        self.max_files = max_files

    def get_output_path(self, prompt_id: str) -> Path:
        """
        Return the full path for a prompt output file.
        """
        return self.output_dir / f"{prompt_id}.txt"

    def initialize(self, request: PromptRequest) -> str:
        """
        Prepare storage for a new execution.

        Returns:
            Path to the output file as a string
        """
        if not request.metadata.get("persist", True):
            return ""

        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)

            output_path = self.get_output_path(request.prompt_id)
            if request.metadata.get("append_existing", False):
                output_path.touch(exist_ok=True)
            else:
                output_path.write_text("", encoding="utf-8")

            return str(output_path)

        except OSError as error:
            raise StorageError(
                f"Failed to initialize output for prompt_id='{request.prompt_id}'"
            ) from error

    def append(self, request: PromptRequest, text: str) -> None:
        """
        Append streamed text to the output file.
        """
        if not request.metadata.get("persist", True):
            return

        output_path = self.get_output_path(request.prompt_id)

        try:
            with output_path.open("a", encoding="utf-8") as file:
                file.write(text)
                file.flush()

        except OSError as error:
            raise StorageError(
                f"Failed to append output for prompt_id='{request.prompt_id}'"
            ) from error

    def finalize(self, request: PromptRequest) -> None:
        """
        Finalize output and enforce retention policy.
        """
        if not request.metadata.get("persist", True):
            return

        output_path = self.get_output_path(request.prompt_id)

        if not output_path.exists():
            raise StorageError(
                f"Cannot finalize missing output for prompt_id='{request.prompt_id}'"
            )

        self._enforce_retention(request)

    def _enforce_retention(self, request: PromptRequest) -> None:
        """
        Apply simple retention policies.

        Supports:
        - max_files (global cap)
        - max_age_seconds (per-request)
        """
        try:
            files = sorted(
                self.output_dir.glob("*.txt"),
                key=lambda p: p.stat().st_mtime,
            )

            # Global file count cap
            if self.max_files is not None:
                while len(files) > self.max_files:
                    oldest = files.pop(0)
                    oldest.unlink(missing_ok=True)

            # Per-request age-based cleanup
            max_age = request.metadata.get("max_age_seconds")
            if max_age is not None:
                import time

                now = time.time()

                for file in files:
                    age = now - file.stat().st_mtime
                    if age > max_age:
                        file.unlink(missing_ok=True)

        except OSError as error:
            raise StorageError("Failed during retention enforcement") from error
