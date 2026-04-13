# Text-to-Text Architecture

## Overview

The `text2text` module handles execution of text prompts and persistence of streamed text output.

---

## 🧱 Components

### Executor

Entry point for execution:

```python
execute(request, backend, storage)
```

Responsibilities:

- coordinate execution

- iterate over backend output

- pass output to storage

---

### Backend

Located in:

```text
backends/
```

Responsibilities:

- send prompt to model

- yield text output

---

### Storage

Responsible for:

- creating output file

- appending streamed text

- finalizing output

---

## 🔄 Execution Flow

```text
Request
  ↓
Executor
  ↓
Backend (stream text)
  ↓
Executor loop
  ↓
Storage (append text)
```

---

## 🧠 Design Decisions

- streaming is handled within this module

- persistence is text-specific

- no assumptions are shared with other modalities

---

## 📌 Behavior

- output is append-only

- file is readable during execution

- execution is controlled entirely within this module

---

## 🧠 Summary

The `text2text` module encapsulates all behavior required for text-based generation, including backend interaction, streaming, and persistence.
