# Text-to-Text (text2text)

The `text2text` modality provides execution of text prompts against language model backends.

---

## 🧠 Overview

This module implements the following pattern:

> Text input → language model → streamed text output → persisted text file

---

## 🚀 Usage

```python
from ysparr.modalities.text2text.executor import execute
```

Example (conceptual):

```python
execute(
    request,
    backend=KoboldCPPBackend(...),
    storage=TextFileStorage(...)
)
```

---

## 🧩 Responsibilities

The `text2text` module is responsible for:

- invoking the backend

- handling streamed output

- writing output to a text file

- managing execution flow

---

## 💾 Output

Output is written as plain text.

Typical behavior:

- output is streamed incrementally

- text is appended to a file

- file is readable during execution

---

## 🔌 Backends

Backends are located in:

```text
backends/
```

Each backend:

- connects to a specific system

- yields text output

---

## 🧠 Summary

The `text2text` modality provides a complete implementation of text-based execution using the Ysparr pattern.
