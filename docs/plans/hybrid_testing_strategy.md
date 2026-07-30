# Hybrid Testing Strategy for Apmatia

## Context

Apmatia is a modular Python system with autonomous agent loops, AI model management, contacts/discussions, IPE (Intelligent Process Engine), and various supporting modules. The codebase uses a clean architecture pattern with ports/adapters, dataclasses for models, and Protocol-based interfaces for dependencies.

Many module behaviors depend on LLM outputs—prompt parsing, tool selection from free text, response formatting, state transitions driven by AI decisions. Testing these with only mocks can miss real-world issues; testing all with real AI calls can be slow and flaky.

## Goal

A hybrid testing strategy with three complementary layers:
1. **Mock-based unit tests** – fast, deterministic
2. **Real AI tests** – slower, realistic
3. **Two-AI evaluation** – scoring/validating AI output

Applied across Apmatia's modules, starting with `agent_loops`.

---

## 1. Mock-Based Unit Tests (Fast, Deterministic)

### Purpose
Logic, state transitions, error handling, boundary conditions.

### Examples
- Task state machine transitions
- Event persistence
- ModelRequest construction
- ToolExecutor protocol compliance
- [`AgentLoopExecutor.execute()`](src/apmatia/modules/agent_loops/executor.py:47) – state transitions, event logging, error handling
- [`AgentLoopTask`](src/apmatia/modules/agent_loops/models.py:200) – serialization, state machine
- [`ToolCallStreamFilter`](src/apmatia/modules/agent_loops/service.py:112) – parsing tool call markers
- [`DefaultStaticModelExecutor`](src/apmatia/modules/agent_loops/service.py:168) – fallback behavior

### Shared Fixtures (conftest.py)
```python
# Shared model factories
def make_task(): ...
def make_event(): ...
def make_tool_result(): ...

# Mock implementations
class MockModelExecutor: ...
class MockToolExecutor: ...
class MockTaskRepository: ...
```

---

## 2. Real AI Tests (Slower, Realistic)

### Purpose
Prompt/response parsing, tool selection from free text, AI-driven behavior.

### Examples
- LLM parses tool call from text
- Prompt template renders correctly
- Agent chooses appropriate tool for task
- Response format matches expected schema

### For `agent_loops` Module
- Full loop execution with real LLM: prompt → tool selection → response → state transition
- Tool call parsing from actual model output
- Multi-turn conversation flow
- Edge cases: model returns invalid JSON, model doesn't call a tool, model calls multiple tools

### For Other Modules
| Module | Real AI Focus |
|--------|---------------|
| [`ai_model_manager`](src/apmatia/modules/ai_model_manager/module.py) | Model selection from workload |
| [`discuss`](src/apmatia/modules/discuss/module.py) | Summarization, tagging from AI |
| [`ipe`](src/apmatia/modules/ipe/module.py) | Prompt → action selection |
| [`agent_alarms`](src/apmatia/modules/agent_alarms/module.py) | Alarm text generation |
| [`agent_config`](src/apmatia/modules/agent_config/module.py) | Prompt template generation |

---

## 3. Two-AI Evaluation (LLM-as-a-Judge)

### How It Works
- **First AI** (`--ai-endpoint`): Generates the actual test output (e.g., tool selection, response text, state transition).
- **Second AI** (`--judge-endpoint`): Evaluates that output and returns structured data (e.g., `{"score": 0.85, "correct": true, "reasoning": "..."}`).

### Benefits
- Avoids hard-coded expected values (which don't work well for open-ended AI output).
- Enables programmatic scoring of AI behavior without hard-coded expected values.
- Can capture nuance: "mostly correct but missing X," "reasonable alternative," etc.

### Considerations
- Adds another API call per test (slower, more cost).
- The judge LLM itself can be imperfect (choose a capable model).
- Structured output parsing may need fallback handling.

### Use Cases
- Scoring response quality across model versions.
- Validating tool selection appropriateness.
- Tracking trends over time (e.g., "model v2 scores 10% higher").

---

## Test File Organization

```
apmatia/tests/
├── unit/                          # Mock-based unit tests (fast, deterministic)
│   ├── test_agent_loops_service.py
│   ├── test_agent_loops_executor.py
│   ├── test_agent_loops_models.py
│   ├── test_ai_model_manager.py
│   ├── test_discuss.py
│   └── ...
│
├── integration/                   # Real AI call tests (slower, realistic)
│   ├── test_agent_loops_ai.py     # Agent loop with actual LLM
│   ├── test_agent_prompts_ai.py   # Prompt generation with actual LLM
│   ├── test_ipe_ai.py             # IPE with actual LLM
│   └── ...
│
└── conftest.py                    # Shared fixtures (mock and AI)
```

---

## Design Options

### Option A: Separate Files (Recommended)
- `unit/test_agent_loops_service.py` – mocks
- `integration/test_agent_loops_ai.py` – real AI

**Pros:** Clear separation, easy to run subsets, avoids DRY violations in test logic.
**Cons:** Some fixture duplication (managed via conftest).

### Option B: Same File, Marked Tests
- `test_agent_loops.py` with `@pytest.mark.ai` for real AI tests

**Pros:** Single file per feature.
**Cons:** Mixed concerns, harder to filter when running tests.

### Option C: Parametrized Executor
- Same test, parametrized with `MockModelExecutor` and `RealModelExecutor`

**Pros:** Maximum DRY.
**Cons:** Complex fixtures, harder to debug, slower when all run.

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Real AI tests are slow | Run only a subset in CI; use mocks for most tests |
| Real AI tests can be flaky | Set explicit timeouts; retry on failure; capture outputs for debugging |
| DRY violations between mock/real tests | Shared fixtures in conftest; helper functions for common assertions |
| AI endpoint configuration | Env var `AI_TEST_ENDPOINT`; default to mock if not set |

---

## Suggested First Steps

1. **Start with `agent_loops`:**
   - Audit existing tests in `tests/unit/test_agent_loops_*.py`
   - Create `tests/integration/test_agent_loops_ai.py` with 3–5 real AI tests

2. **Define Shared Fixtures:**
   - Add model factories and mock implementations to `conftest.py`
   - Add `ai_model_endpoint` and `real_model_executor` fixtures

3. **Expand to Other Modules:**
   - Pick 1–2 modules (e.g., `ipe`, `agent_alarms`)
   - Add 2–3 real AI tests per module

4. **CI Configuration:**
   - Run all unit tests on every push
   - Run integration AI tests on manual trigger or nightly

---

## Notes

- The AI endpoint (e.g., `192.x.x.x:8080`) is passed as a command-line argument `--ai-endpoint` or env var `AI_TEST_ENDPOINT`.
- If no endpoint is provided, tests run with mocks only (fast, deterministic).
- If an endpoint is provided, tests use the real LLM at that address (slower, realistic).
- **Two-AI Evaluation (optional):** A second `--judge-endpoint=<host:port>` can be provided for LLM-as-a-Judge evaluation.
  - The first AI generates the test output (e.g., tool selection, response text).
  - The second AI evaluates that output and returns structured data (e.g., JSON with score, correctness, reasoning).
  - This enables programmatic scoring of AI behavior without hard-coded expected values.
- This strategy scales: new modules follow the same pattern.
