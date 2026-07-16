# Hai TDD: M0-A Inspect Execution Validation

## Cycle 1: Frozen Run Contract

### Target Behavior

An `ExecutionRunSpec` round-trips through stable JSON and rejects mutation after construction.

### RED

- **Test added**: `tests/unit/domain/test_models.py::{test_execution_run_spec_round_trips_stable_json,test_execution_run_spec_is_frozen}`
- **Behavior asserted**: project run contracts serialize deterministically and are immutable.
- **Command**: `pytest tests/unit/domain/test_models.py -q`
- **Observed failure**: `ModuleNotFoundError: No module named 'agentsec_eval.domain'`.
- **Failure is correct because**: the new project-owned domain boundary did not exist; test imports and
  Pydantic were otherwise valid.

### GREEN

- **Minimal implementation**: added five frozen Pydantic models and package exports.
- **Command**: `pytest tests/unit/domain/test_models.py -q`
- **Observed pass**: `2 passed`.

### REFACTOR

- **Refactor done**: no.
- **Change**: no refactor was needed for the minimal five-model slice.
- **Command after refactor**: not needed.
- **Observed result**: the GREEN result remained the cycle evidence.

### Next Behavior

Positive execution budgets and canonical trace invariants.

## Cycle 2: Trace Invariants

### Target Behavior

Budgets require positive limits; canonical trace events round-trip through JSON; a trace rejects an
empty list, wrong Run ID, duplicate event ID, or non-increasing sequence.

### RED

- **Test added**: budget and trace cases in `tests/unit/domain/test_models.py`.
- **Behavior asserted**: minimal run limits and trace identity/order are enforced by project code.
- **Command**: `pytest tests/unit/domain/test_models.py -q`
- **Observed failure**: `ImportError: cannot import name 'CanonicalTraceEvent'`.
- **Failure is correct because**: the frozen run types existed, but trace contracts and validation had
  not been implemented.

### GREEN

- **Minimal implementation**: added positive budget fields, literal event/strength vocabularies,
  JSON-only trace payloads, and `validate_trace`.
- **Command**: `pytest tests/unit/domain/test_models.py -q`
- **Observed pass**: `10 passed`.

### REFACTOR

- **Refactor done**: yes.
- **Change**: moved `Sequence` to `collections.abc` and removed an unnecessary MyPy ignore after
  quality checks identified both issues.
- **Command after refactor**: focused Pytest, Ruff check/format, and MyPy commands.
- **Observed result**: `10 passed`; Ruff clean; format clean; MyPy clean over three files.

### Next Behavior

Inspect-independent Target Session protocols and HTTP session adapter behavior.
