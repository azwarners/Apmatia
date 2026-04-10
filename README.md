# Apmatia

**Apmatia Packs Minimal AI Tools Into an Application**

Apmatia is an API-first, self-hosted application framework for building modular AI-powered systems using lightweight, composable libraries.

---

## 🧠 What This Is

Apmatia is a structured system for integrating AI capabilities into real applications without bloated frameworks.

It enforces a clean architecture where:

- **Libraries** contain all functionality (e.g., ysparr)

- **Core** orchestrates libraries

- **API (internal)** is the single programmatic interface

- **API (HTTP)** exposes the system

- **Interfaces (CLI, web, etc.)** consume the same API

---

## 🔁 Execution Flow

All requests follow a single path:

```
Interface → API (internal) → Core → Library → External Service (LLM)
```

This guarantees:

- consistent behavior across interfaces

- no duplicated logic

- clean extensibility

---

## 🚀 Features

- FastAPI-based HTTP server

- CLI interface using the same execution path

- Docker-first deployment

- Modular library integration (ysparr)

- Local LLM support via KoboldCpp

- Config file-based configuration

- Web UI with modular Web Components for settings categories

- Pytest test suite (unit + integration)

---

## 🧠 Current Integration

Apmatia currently integrates:

- **ysparr** → minimal execution library

- **KoboldCpp** → local LLM backend

---

## ⚙️ Configuration

Apmatia stores runtime config in:

```
~/.config/apmatia/config.json
```

This is now the primary configuration source.

`.env` is optional and only used as a fallback/bootstrap source. If set, values are saved into the config store.

Common config keys in `config.json`:

```json
{
  "llm": {
    "backend": "openai_compatible",
    "max_tokens": 8192,
    "openai_compatible": {
      "base_url": "http://localhost:5001",
      "api_key": null,
      "model_name": null
    },
    "koboldcpp": {
      "base_url": "http://localhost:5001"
    }
  },
  "discussion": {
    "system_prompt": ""
  },
  "ui": {
    "theme": "dark",
    "font_family": "system-ui",
    "font_size": 16
  }
}
```

You can edit these values in the web app at `/settings`.
Settings are grouped by collapsible categories and backed by reusable Web Components:

- `AI Settings`
- `Discussion Settings`
- `Theme Settings`

---

## ▶️ Run the Application

```
./start.sh
```

Then open:

```
http://localhost:8000
```

---

## 💻 CLI Usage

```
python -m src.interfaces.cli.main "Say hello"
```

---

## 🧪 Run Tests (Docker)

```
docker compose run --rm app pytest
```

---

## 🏗️ Project Structure

```
src/
├── libraries/   → business logic (ysparr)
├── core/        → orchestration
├── api/internal → canonical interface
├── api/http     → HTTP layer
├── interfaces/  → CLI + web
```

---

## 🏭 Philosophy

- One execution path

- No duplicated logic

- Libraries are independent

- Interfaces are clients

- Keep everything minimal

---

## 🚧 Roadmap

- Model manager

- Multi-model routing

- Multi-user support

---

## 💬 Summary

Apmatia is a lightweight foundation for building AI-powered systems that:

- stay modular

- avoid framework lock-in

- scale cleanly
