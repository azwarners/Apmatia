# Repo Misroute Recovery Note

This document exists because a long Apmatia task was executed against the wrong checkout.
It is intended to help the next session recover quickly, avoid repeating the mistake, and
make it obvious which repository should be treated as the source of truth.

## Short Version

The work in the modular-architecture task was applied to:

- **wrong checkout:** `/home/nick/apmatia`
- **intended checkout:** `/home/nick/ServerData/repos/apmatia`

If you are starting a new Codex session for Apmatia, treat `/home/nick/ServerData/repos/apmatia`
as the only repository to modify unless the user explicitly says otherwise.

## What Went Wrong

A Codex session was started with `/home/nick/apmatia` as the active working directory.
That session performed edits, tests, and container redeploys in that tree even though the user
was working in the repository at `/home/nick/ServerData/repos/apmatia`.

The user’s IDE being open on the correct repo was not enough to move the Codex session.
The actual workspace for the session was still the old checkout.

## Why This Matters

The two checkouts are not interchangeable:

- they have different filesystem roots
- they may have different git histories or local changes
- edits in one tree do not appear in the other
- tests and redeploys run against the tree the session is actually bound to

That means anything changed in `/home/nick/apmatia` should be treated as separate from the
real working repository unless it is intentionally copied or ported over.

## What Was Done In The Wrong Checkout

The modular-architecture work and the related documentation updates were performed in the wrong tree.
The work should be considered to live in `/home/nick/apmatia`, not in the intended repository.

From the conversation and the on-disk verification that followed, the misrouted work included:

- module-first architecture documentation updates
- registry/module terminology cleanup
- bundled-versus-workspace module language
- module creation guidance
- architecture documentation changes
- a module scaffolding guide
- a small AGENTS reminder about preferring modules
- test execution and redeployment steps performed against the wrong checkout

If you are trying to reconstruct the code state, assume that any module-system changes created during
that task need to be audited and possibly recreated in `/home/nick/ServerData/repos/apmatia`.

## Files That Were Touched In The Wrong Checkout

The following files were updated in `/home/nick/apmatia` during the mistaken session:

- `README.md`
- `docs/ARCHITECTURE.md`
- `docs/CREATING_MODULES.md`
- `AGENTS.md`

In addition, the session executed the full test suite and redeployed the app containers from the wrong
checkout.

## What The Next Session Should Do

When you reopen Codex for Apmatia, start in the correct repository and verify it explicitly before
changing anything:

1. Confirm the working directory with `pwd`.
2. Confirm the git top-level with `git rev-parse --show-toplevel`.
3. Confirm that the repo root is `/home/nick/ServerData/repos/apmatia`.
4. Read the repo’s `AGENTS.md` before making changes.
5. Check `git status` so you know what is already modified.
6. Only then start editing files.

## Recovery Checklist

If the modular architecture work still needs to exist in the correct repository, the next session should:

1. Identify the complete set of changes made in `/home/nick/apmatia`.
2. Compare them against `/home/nick/ServerData/repos/apmatia`.
3. Port any missing code, tests, and docs into the correct repo.
4. Re-run the full test suite in the correct repo.
5. Redeploy the correct repo’s core and Streamlit containers.

## Practical Guardrails For Future Work

Use these rules to avoid repeating the mistake:

- Do not assume the active VS Code window determines Codex’s working directory.
- Do not assume the correct repo is the same as the currently open folder unless the session was
  launched there.
- Treat the filesystem root of the session as authoritative.
- Verify the repo path before making any edits.
- If the user names a repo path, use that exact path and ignore similarly named folders.

## Suggested Start Of Every New Session

Before touching files, run something equivalent to:

```bash
pwd
git rev-parse --show-toplevel
```

If the answer is not `/home/nick/ServerData/repos/apmatia`, stop and correct the workspace first.

## Notes For Human Readers

This file is intentionally verbose because the failure mode here was not a small typo.
It was a workspace-selection error that caused a large amount of work to land in the wrong checkout.
The safest recovery is to keep the instruction unambiguous and impossible to miss.

## Bottom Line

- The wrong checkout used during the task was `/home/nick/apmatia`.
- The correct checkout is `/home/nick/ServerData/repos/apmatia`.
- Future Apmatia work should start in the correct checkout and verify the path before editing.
