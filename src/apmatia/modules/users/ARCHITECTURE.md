# Users Module

This stable infrastructure module owns Apmatia's user/group domain and persistence layer.

## Goals

- Keep user/group business logic modular and reusable.
- Support user-private and group-shared data ownership (`uid`/`gid` style).
- Use the stable persistence module (`SQLiteStore`) behind repository boundaries.
- Keep Apmatia runtime wiring outside this package.

## Package Layout

- `models.py`: domain entities and enums.
- `repositories.py`: persistence-facing contracts.
- `services.py`: use-case-facing contracts.
- `manager.py`: orchestration entrypoints (`UserManager`, `GroupManager`, `AccessController`).
- `sqlite_repositories.py`: SQLite adapter wired to `apmatia.modules.persistence.SQLiteStore`.

## Planned Flow

`API (internal)` -> `modules.users.runtime` -> users-module managers -> repository interfaces -> SQLite adapter

## Notes

- This package already uses package-relative imports to stay portable across package roots.
- Apmatia-specific env/path/runtime state (`APMATIA_HOME`, `APMATIA_DATA_DIR`, DB location) lives in `runtime.py`.
