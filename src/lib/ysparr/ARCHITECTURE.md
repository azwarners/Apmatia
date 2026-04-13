# Ysparr Architecture

## Overview

Ysparr is a modular system for executing generative AI tasks.

It separates shared structure from modality-specific behavior.

---

## 🧱 Architectural Model

```text
Application / Library
        ↓
Modality Module (text2text, text2image, etc.)
        ↓
Core (types, utilities)
```

---

## 🔑 Core Design

The `core` package provides:

- shared data structures

- shared exception types

- minimal execution utilities (if any)

Core does **not**:

- execute prompts directly

- determine modality

- manage streaming

- handle persistence

- interact with backends

---

## 🧩 Modalities

Modalities are the primary units of functionality in Ysparr.

Each modality:

- defines an execution entry point

- integrates with one or more backends

- determines how output is produced

- manages persistence

---

## 🧠 Execution Flow

1. A request is constructed

2. A modality's `execute` function is called

3. The modality:
   
   - calls the backend
   
   - processes output (streaming or otherwise)
   
   - persists results

4. Execution completes

---

## 📦 Separation of Concerns

### Core

- shared structures only

### Modality

- execution logic

- backend integration

- output handling

### Backend

- communication with AI systems

---

## 🔄 General Pattern

```text
Input → Modality → Backend → Output → Persistence
```

---

## 📌 Design Goals

- keep the core minimal and stable

- allow modalities to evolve independently

- avoid cross-modality assumptions

- maintain a consistent mental model across the system

---

## 📚 Modality Documentation

Each modality contains its own detailed documentation:

```text
modalities/<modality>/
├── README.md
└── ARCHITECTURE.md
```

These documents describe:

- execution behavior

- backend usage

- output handling

- design decisions specific to that modality
