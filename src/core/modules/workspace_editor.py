from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .scaffold import validate_module_slug
from .workspace import resolve_module_target_dir


class WorkspaceEditorError(ValueError):
    pass


class WorkspaceModuleNotFoundError(WorkspaceEditorError):
    pass


class WorkspacePathError(WorkspaceEditorError):
    pass


class WorkspaceFileNotFoundError(WorkspaceEditorError):
    pass


@dataclass(frozen=True, slots=True)
class WorkspaceFile:
    relative_path: str
    path: Path
    size_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "relative_path": self.relative_path,
            "path": str(self.path),
            "size_bytes": self.size_bytes,
        }


@dataclass(frozen=True, slots=True)
class WorkspaceFileContent:
    module_slug: str
    module_path: Path
    relative_path: str
    path: Path
    content: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "module_slug": self.module_slug,
            "module_path": str(self.module_path),
            "relative_path": self.relative_path,
            "path": str(self.path),
            "content": self.content,
        }


@dataclass(frozen=True, slots=True)
class WorkspaceWriteResult:
    module_slug: str
    module_path: Path
    relative_path: str
    path: Path
    created: bool
    bytes_written: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "module_slug": self.module_slug,
            "module_path": str(self.module_path),
            "relative_path": self.relative_path,
            "path": str(self.path),
            "created": self.created,
            "bytes_written": self.bytes_written,
        }


@dataclass(frozen=True, slots=True)
class WorkspaceDeleteResult:
    module_slug: str
    module_path: Path
    relative_path: str
    path: Path
    deleted: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "module_slug": self.module_slug,
            "module_path": str(self.module_path),
            "relative_path": self.relative_path,
            "path": str(self.path),
            "deleted": self.deleted,
        }


@dataclass(frozen=True, slots=True)
class ModuleWorkspaceEditor:
    base_dir: Path | None = None

    def list_files(self, slug: str, base_dir: Path | None = None) -> list[WorkspaceFile]:
        editor = self._with_base_dir(base_dir)
        _module_slug, module_dir = editor._require_workspace_module(slug)
        module_root = module_dir.resolve(strict=True)
        results: list[WorkspaceFile] = []

        for path in sorted((item for item in module_dir.rglob("*") if item.is_file()), key=lambda item: str(item.relative_to(module_dir))):
            resolved = path.resolve(strict=True)
            editor._ensure_within_root(resolved, module_root)
            results.append(
                WorkspaceFile(
                    relative_path=str(resolved.relative_to(module_root)),
                    path=resolved,
                    size_bytes=resolved.stat().st_size,
                )
            )
        return results

    def read_file(self, slug: str, relative_path: str, base_dir: Path | None = None) -> WorkspaceFileContent:
        editor = self._with_base_dir(base_dir)
        module_slug, module_dir = editor._require_workspace_module(slug)
        module_root = module_dir.resolve(strict=True)
        file_path = editor._resolve_workspace_file_path(module_root, relative_path)
        if not file_path.exists() or not file_path.is_file():
            raise WorkspaceFileNotFoundError(f"Workspace file not found: {relative_path}")
        return WorkspaceFileContent(
            module_slug=module_slug,
            module_path=module_root,
            relative_path=str(file_path.relative_to(module_root)),
            path=file_path,
            content=file_path.read_text(encoding="utf-8"),
        )

    def write_file(
        self,
        slug: str,
        relative_path: str,
        content: str,
        base_dir: Path | None = None,
        create: bool = True,
    ) -> WorkspaceWriteResult:
        editor = self._with_base_dir(base_dir)
        module_slug, module_dir = editor._require_workspace_module(slug)
        module_root = module_dir.resolve(strict=True)
        file_path = editor._resolve_workspace_file_path(module_root, relative_path, allow_missing=True)
        existed_before = file_path.exists()
        if file_path.exists() and file_path.is_dir():
            raise WorkspacePathError(f"Workspace path points to a directory: {relative_path}")
        if not existed_before and not create:
            raise WorkspaceFileNotFoundError(f"Workspace file not found: {relative_path}")
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        resolved = file_path.resolve(strict=True)
        editor._ensure_within_root(resolved, module_root)
        return WorkspaceWriteResult(
            module_slug=module_slug,
            module_path=module_root,
            relative_path=str(resolved.relative_to(module_root)),
            path=resolved,
            created=not existed_before,
            bytes_written=len(content.encode("utf-8")),
        )

    def delete_file(self, slug: str, relative_path: str, base_dir: Path | None = None) -> WorkspaceDeleteResult:
        editor = self._with_base_dir(base_dir)
        module_slug, module_dir = editor._require_workspace_module(slug)
        module_root = module_dir.resolve(strict=True)
        file_path = editor._resolve_workspace_file_path(module_root, relative_path)
        if not file_path.exists() or not file_path.is_file():
            raise WorkspaceFileNotFoundError(f"Workspace file not found: {relative_path}")
        file_path.unlink()
        return WorkspaceDeleteResult(
            module_slug=module_slug,
            module_path=module_root,
            relative_path=str(file_path.relative_to(module_root)),
            path=file_path,
            deleted=True,
        )

    def _with_base_dir(self, base_dir: Path | None) -> "ModuleWorkspaceEditor":
        if base_dir is None:
            return self
        return ModuleWorkspaceEditor(base_dir=base_dir)

    def _require_workspace_module(self, slug: str) -> tuple[str, Path]:
        module_slug = validate_module_slug(slug)
        module_dir = resolve_module_target_dir(module_slug, workspace=True, base_dir=self.base_dir)
        if not module_dir.exists() or not module_dir.is_dir():
            raise WorkspaceModuleNotFoundError(f"Workspace module not found: {module_slug}")
        return module_slug, module_dir

    def _resolve_workspace_file_path(
        self,
        module_root: Path,
        relative_path: str,
        *,
        allow_missing: bool = False,
    ) -> Path:
        safe_relative_path = self._validate_relative_path(relative_path)
        target = module_root / safe_relative_path
        if target.exists():
            resolved = target.resolve(strict=True)
            self._ensure_within_root(resolved, module_root)
            return resolved

        if allow_missing:
            self._ensure_within_root(target.parent.resolve(strict=False), module_root)
            return target

        raise WorkspaceFileNotFoundError(f"Workspace file not found: {relative_path}")

    @staticmethod
    def _validate_relative_path(relative_path: str) -> Path:
        path = Path(relative_path)
        if not relative_path or str(path) in {".", ""}:
            raise WorkspacePathError("Workspace path cannot be empty.")
        if path.is_absolute():
            raise WorkspacePathError("Workspace path must be relative.")
        if any(part == ".." for part in path.parts):
            raise WorkspacePathError("Workspace path cannot contain '..'.")
        if path.drive or path.root:
            raise WorkspacePathError("Workspace path must not include a drive or root.")
        return path

    @staticmethod
    def _ensure_within_root(path: Path, root: Path) -> None:
        try:
            path.relative_to(root)
        except ValueError as exc:
            raise WorkspacePathError("Workspace path resolves outside the module root.") from exc
