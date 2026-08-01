# ADR: Linux-First Flet Migration Strategy

## Decision

The first Flet product is the **Apmatia Linux Client** - a native desktop application for Linux that connects to headless Apmatia Core over the existing API and portable view-contract boundary.

## Status

Accepted

## Approval

- Decision owner: Nick
- Approved: 2026-08-01
- Approval: Nick approved the Phase 0 Linux-first migration boundary.

## Context

Apmatia is migrating from Streamlit to Flet to provide native desktop and mobile applications. The migration needs a clear product boundary to avoid over-engineering and ensure a working product before expanding to other platforms.

## Decision Drivers

- Linux desktop provides a stable, well-understood development and testing environment
- Desktop experience should be proven before mobile adaptation
- Clear separation between shared infrastructure and platform-specific code
- Gradual migration path that maintains existing functionality

## Consequences

### Positive

- Single, focused product target for initial migration
- Desktop experience can be optimized for keyboard and pointer interaction
- Clear path for Android client development after Linux success
- Shared infrastructure can be extracted from proven commonality

### Negative

- Android client development is deferred until after Linux client proves architecture
- Some shared infrastructure may need adjustment when Android is added

## Linux-First Decisions

1. **The first Flet product is the Apmatia Linux Client**
2. **Linux desktop is the development and testing target**
3. **The Linux client connects to headless Apmatia Core**
4. **Streamlit remains available during migration**
5. **Android is deferred until after the Linux client proves the architecture**
6. **Android reuse is desirable but not guaranteed for every shell, layout, or component**
7. **Linux-specific desktop behavior is allowed and expected**

## Architecture Boundary

- **Apmatia Core** remains a headless Python service (may run locally, in container, on home server, or remote host)
- **Apmatia Linux Client** is a native Flet desktop application
- **Apmatia Android Client** (later) may reuse compatible infrastructure

## Acceptance Criteria

- The repository and implementation plan clearly name the Apmatia Linux Client
- No phase treats the first seven steps as an unspecified generic client
- Android work is explicitly out of scope until the later Android phase

## Phase 0 Scope Clarification

Phase 0 establishes and records the product boundary. It does not require
implementation or acceptance of login, rendering, packaging, Android support,
or Streamlit replacement.

Exploratory implementation that already exists in the repository is retained.
That work is subject to the discovery, review, tests, and acceptance criteria
of the phase where it is formally evaluated; its existence does not imply that
the corresponding later phase is complete.
