## Ysparr

**Ysparr Sends Prompts And Receives Responses**

Ysparr is a modular execution library for generative AI systems.

It provides a consistent pattern for interacting with AI backends:

> Provide input → execute → receive output → persist result

---

## 🧠 Overview

Ysparr is organized around **modalities**.

Each modality represents a specific type of generative task, such as:

- text-to-text

- text-to-image

- text-to-speech

- image-to-image

- image-to-3D / mesh generation

Each modality:

- defines its own execution behavior

- integrates with one or more backends

- handles its own output format and persistence

---

## 🧱 Structure

```text
ysparr/
├── core/
└── modalities/
    ├── text2text/
    ├── text2image/
    ├── text2speech/
    └── ...
```

---

## 🎯 Core Principles

- **Minimal core**  
  Core provides shared types and utilities only.

- **Modality-driven design**  
  All execution logic lives within modality modules.

- **No central execution API**  
  Consumers interact directly with modality entry points.

- **No assumptions across modalities**  
  Each modality defines its own behavior, including:
  
  - streaming vs non-streaming
  
  - file formats
  
  - persistence strategy

---

## 🚀 Usage

Ysparr is used by importing a specific modality.

Example:

```python
from ysparr.modalities.text2text.executor import execute
```

Each modality provides its own usage patterns and configuration.

Refer to the modality-specific documentation for details.

---

## 📚 Documentation

Each modality contains its own documentation:

```text
ysparr/modalities/<modality>/
├── README.md
└── ARCHITECTURE.md
```

These documents describe:

- how to use the modality

- how it interacts with backends

- how it handles output and persistence

---

## 🧠 Summary

Ysparr is a unified library for executing generative AI workloads across multiple modalities.

It achieves this by:

- keeping a minimal shared core

- implementing behavior within modality modules

- maintaining a consistent execution pattern
