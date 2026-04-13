# Core User Management

This package is the reusable user/group domain and persistence layer.

## Goals

- Keep user/group business logic modular and reusable.
- Support user-private and group-shared data ownership (`uid`/`gid` style).
- Use the shared persistence library (`SQLiteStore`) behind repository boundaries.
- Keep Apmatia runtime wiring outside this package.

## Package Layout

- `models.py`: domain entities and enums.
- `repositories.py`: persistence-facing contracts.
- `services.py`: use-case-facing contracts.
- `module.py`: core orchestration entrypoints (`UserManager`, `GroupManager`, `AccessController`).
- `sqlite_repositories.py`: SQLite adapter wired to `persistence.SQLiteStore`.

## Planned Flow

`API (internal)` -> `src/core/user_management_runtime.py` -> `lib.user_management` managers -> repository interfaces -> SQLite adapter

## Notes

- This package already uses package-relative imports to stay portable across package roots.
- Apmatia-specific env/path/runtime state (`APMATIA_HOME`, `APMATIA_DATA_DIR`, DB location) lives in `src/core/user_management_runtime.py`.
