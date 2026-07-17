# M0-B Assertion-Backed PyRIT Scorer Validation Design

## Scope

M0-B validates one narrow adapter boundary:

```text
project ProgressOracle
    -> ProgressDecision
    -> AssertionBackedPyRITScorer
    -> PyRIT true_false Score + lossless project-state metadata
```

The Progress Oracle remains the source of the runtime progress decision. PyRIT receives a boolean
needed by its attack interfaces but does not define project truth. No Attack Strategy or
PromptTarget runs in this milestone.

## Package Boundaries

- `agentsec_eval.assertions` owns `ProgressState`, `ProgressDecision`, and `ProgressOracle` and
  imports no PyRIT module.
- `agentsec_eval.integrations.pyrit` is the only new production package allowed to import PyRIT.
- Existing `domain`, `targets`, and `execution` packages do not import PyRIT.
- `m0a_harness.py` remains frozen validation code and is not an M0-B integration surface.

## Project Decision Contract

`ProgressState` has exactly four values:

- `CONTINUE`
- `OBJECTIVE_ACHIEVED`
- `TERMINAL_BLOCKED`
- `INVALID_RUN`

`AttackStage` has the ordered vocabulary `NONE`, `DELIVERED`, `INFLUENCED`, `ATTEMPTED`, `EXECUTED`,
and `EFFECT`. `ProgressDecision` contains a non-empty `run_id`, state, required `stage_reached`,
JSON-compatible `progress_features`, internal rationale, attacker-safe policy feedback, evidence
IDs, and internal JSON metadata. It is immutable and forbids extra fields. `OBJECTIVE_ACHIEVED`
requires evidence because text alone cannot prove an environmental effect. The two terminal
non-success states remain distinguishable.

`internal_rationale` is audit-only and may contain private evidence detail. `policy_feedback` is the
only decision text allowed in PyRIT `Score.score_rationale`; the Oracle implementation owns its
sanitization. The complete decision remains in score metadata for trusted project recovery, but an
Attack Policy must never expose that internal metadata to an adversarial model.

`ProgressOracle.evaluate()` is asynchronous and receives the scorer's explicit bound `run_id` plus
the candidate response. Implementations may inspect environment state; the response cannot select
the Run.

## PyRIT Mapping

| Project state | PyRIT value | Terminal | Stop reason | Invalid Run |
|---|---:|---:|---|---:|
| `CONTINUE` | `False` | `False` | empty | `False` |
| `OBJECTIVE_ACHIEVED` | `True` | `True` | `objective_achieved` | `False` |
| `TERMINAL_BLOCKED` | `False` | `True` | `blocked` | `False` |
| `INVALID_RUN` | `False` | `True` | `invalid_run` | `True` |

The score metadata schema is version `1` and stores:

- flat scalar fields used later by M0-C: schema version, Run ID, progress state, terminal,
  stop reason, invalid-run flag, and stage reached;
- the complete `ProgressDecision.model_dump_json()` value for lossless recovery.

PyRIT `0.14.0` constrains metadata values to scalars, so nested project state is JSON text rather
than a lossy flattening. Its Pydantic metadata model normalizes Python booleans to integers because
the declared scalar union excludes `bool`; the flat `terminal` and `invalid_run` flags therefore use
unambiguous lowercase `"true"` / `"false"` strings. A decision whose `run_id` differs from the
scorer's bound Run becomes a new `INVALID_RUN` decision for the bound Run. The foreign decision's
evidence is discarded.

## Scorer Shape

`AssertionBackedPyRITScorer` subclasses PyRIT `TrueFalseScorer` and uses a text-only one-piece
validator. It overrides the protected message-level `_score_async()` extension point so the public
`score_async()` path always calls the project Oracle for normal, blocked, and other-error
single-piece responses instead of accepting PyRIT's metadata-free fallback. Blocked
partial content is passed to the Oracle when present. `_score_piece_async()` remains the required
piece-level implementation, and `_build_identifier()` uses PyRIT's supported subclass API. Each
instance requires one non-empty Run ID and one `ProgressOracle`.

`AttackScoringConfig(objective_scorer=scorer)` is the compatibility gate. The adapter does not
instantiate or run an Attack Strategy.

## Concurrency Proof

A deterministic test Receiver records Canary evidence by Run. A test Oracle implements the public
project protocol over that Receiver. Two scorer instances bound to distinct Runs execute
concurrently. Each result must contain only its bound Run, decision, and evidence IDs. This proves
adapter instance isolation; it does not claim isolation of PyRIT's process-global CentralMemory.

## Dependency and CI Boundary

Core dependencies remain unchanged. The optional extra pins `pyrit==0.14.0`. The normal `quality`
and `m0a-docker` jobs keep installing `.[dev]`; a separate `m0b-pyrit` job installs
`.[dev,pyrit]` and runs only M0-B integration tests plus its compatibility unit tests.

## Explicit Non-Goals

- No `BaseScenario`, `ScenarioCase`, AttackSeed, Registry, Benchmark Adapter, or dataset.
- No PyRIT PromptTarget, multi-turn attack, policy stopping, budget loop, or provider credential.
- No Final Assertion Engine or formal security outcome model.
- No `references/manifest.yaml` change before Draft PR #5 merges.
- No claim that `False` means safe: terminal metadata must be interpreted by M0-C.
- No implementation of policy feedback consumption; M0-B only prevents internal rationale from
  becoming PyRIT adversarial feedback by default.
