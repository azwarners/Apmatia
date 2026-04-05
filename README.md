# Ampcawmutt

**Ampcawmutt is My Python Core API With Multiple UIs and Tests Template**

A reusable, API-first template for building self-hosted Python applications with multiple interfaces (CLI, web, mobile) that all share a single execution path.

---

## 🧠 What This Is

Ampcawmutt is not just a starter project—it is a **structured application system**.

It enforces a clean architecture where:

- **Libraries** contain all business logic
- **Core** coordinates libraries (no logic of its own)
- **API (internal)** is the single programmatic interface
- **API (HTTP)** exposes the system over the network
- **Interfaces (CLI, web, etc.)** all consume the same API

This guarantees consistency across every interface and prevents architectural drift.

---

## 🔁 Execution Flow

Every request follows the same path:

```
Library → Core → API (internal) → API (HTTP or CLI)
```

This means:

- CLI and HTTP always behave identically
- Logic is never duplicated
- New interfaces can be added without rewriting the system

---

## 🚀 Features

- FastAPI-based HTTP server
- CLI interface using the same internal API
- Dockerized runtime
- Virtual environment for development
- Pytest-based test suite (unit + integration)
- Example "hello world" library wired through the full stack

---

## ▶️ Run the Application

```
./start.sh
```

Then open:

```
http://localhost:8000/api/hello
```

---

## 💻 CLI Usage

```
python -m src.interfaces.cli.mainpython -m src.interfaces.cli.main Nick
```

---

## 🧪 Run Tests

```
source .venv/bin/activate./test.sh
```

---

## 🏗️ Project Structure

```
libraries/   → business logiccore/        → orchestrationapi/internal → canonical interfaceapi/http     → network layerinterfaces/  → CLI + web clients
```

---

## 🏭 Purpose

This template is designed to be **cloned and reused**.

Each new project should:

1. Replace the example library (`hello_world`)
2. Implement a real feature
3. Keep the architecture intact

---

## 💬 Philosophy

- One execution path
- No duplicated logic
- Interfaces are clients, not owners
- Architecture is enforced by structure
