# Core User Management Skeleton

This package is a contract-first skeleton for multi-user Apmatia support.

## Goals

- Keep core orchestration modular.
- Support user-private and group-shared data ownership (`uid`/`gid` style).
- Use the shared persistence library (`SQLiteStore`) behind repository boundaries.
- Delay implementation details until we lock behavior and API contracts.

## Package Layout

- `models.py`: domain entities and enums.
- `repositories.py`: persistence-facing contracts.
- `services.py`: use-case-facing contracts.
- `module.py`: core orchestration entrypoints (`UserManager`, `GroupManager`, `AccessController`).
- `sqlite_repositories.py`: SQLite adapter skeleton wired to `persistence.SQLiteStore`.

## Planned Flow

`API (internal)` -> `core.user_management` managers -> repository interfaces -> SQLite adapter

## Notes

- No hashing, validation, schema migration, or query logic is implemented yet.
- All behavior methods intentionally raise `NotImplementedError`.
- This is designed so the package can later move to `src/libraries/` with minimal refactor.

