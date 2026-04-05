# Architecture

Ampcawmutt is designed around a **strict, API-first layered architecture**.

The goal is to enforce a single execution path and prevent logic duplication across interfaces.

---

## 🧠 Core Principle

All functionality flows in one direction:

```text
Libraries → Core → API (internal) → Interfaces
```

No layer is allowed to bypass another.

---

## 🧱 Layers

### 1. Libraries (Business Logic)

**Location:** `src/libraries/`

Libraries contain all real functionality.

They:

- implement features

- contain domain logic

- are completely independent of the rest of the system

They do NOT:

- know about APIs

- know about HTTP

- know about CLI or UI

> Libraries should be reusable outside of this application.

---

### 2. Core (Orchestration)

**Location:** `src/core/`

Core coordinates libraries.

It:

- calls one or more libraries

- combines results

- defines application-level behavior

It does NOT:

- implement business logic

- expose interfaces

- handle HTTP or CLI concerns

> Core is the glue, not the brain.

---

### 3. API (Internal)

**Location:** `src/api/internal/`

This is the **canonical interface** of the system.

Everything that wants to interact with the application must go through this layer.

It:

- exposes core functionality as simple functions

- provides a stable contract for all interfaces

It does NOT:

- contain business logic

- depend on HTTP

> This is the single source of truth for how the system is used programmatically.

---

### 4. API (HTTP)

**Location:** `src/api/http/`

This layer exposes the internal API over the network using FastAPI.

It:

- defines routes

- handles request/response formatting

- maps HTTP calls to internal API functions

It does NOT:

- call libraries directly

- contain business logic

> HTTP is just a transport layer.

---

### 5. Interfaces (CLI, Web, etc.)

**Location:** `src/interfaces/`

Interfaces are clients of the internal API.

They:

- call `api/internal`

- present results to users

- provide different ways to interact with the system

Examples:

- CLI

- web UI

- mobile UI

- future game interfaces

They do NOT:

- call core directly

- implement business logic

> Interfaces are consumers, not owners.

---

## 🔁 Execution Flow

All interactions follow the same path:

```text
Interface → API (internal) → Core → Library
```

For HTTP:

```text
HTTP → API (http) → API (internal) → Core → Library
```

This ensures:

- consistent behavior across all interfaces

- no duplicated logic

- easy extensibility

---

## 🚫 Rules (Strict)

- Core is ONLY called by the internal API

- Libraries are ONLY called by core

- Interfaces NEVER call core or libraries directly

- HTTP NEVER calls core directly

---

## 🎯 Design Goals

- **Single execution path**

- **Separation of concerns**

- **Reusability of libraries**

- **Consistency across interfaces**

- **Ease of extension**

---

## 🏭 Extending the System

To add a new feature:

1. Create or extend a library

2. Add orchestration in core

3. Expose it via the internal API

4. Optionally expose via HTTP or CLI

No existing layers should be modified beyond what is necessary.

---

## 💬 Summary

Ampcawmutt enforces a clean architecture where:

- logic lives in one place

- access is centralized

- interfaces remain thin

- the system scales without becoming tangled

This structure is designed to be copied and reused across multiple applications.
