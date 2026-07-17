# M0-C PyRIT Attack Policy Validation

## Scope

M0-C validates one project-controlled PyRIT `0.14.0` Attack Policy inside one Run:

```text
open TargetSession
-> TargetSessionPromptTarget
-> project-controlled RedTeamingAttack._perform_async
-> AssertionBackedPyRITScorer
-> AttackPolicyResult
```

It is a bounded embedding validation. It is not a production Execution Backend, Campaign
Controller, Benchmark Adapter, Scenario Registry, Final Assertion Engine, `RunOutcome`, or
parallel PyRIT policy backend.

## Runtime Boundaries

- `TargetSessionPromptTarget` adapts exactly one already-open project `TargetSession` to PyRIT's
  final public `PromptTarget.send_prompt_async()` path. It neither opens nor closes a Target.
- `PyRITAttackPolicy` constructs the PyRIT adversarial strategy and owns the single-Run stopping
  policy. It uses `ExecutionBudget.max_turns` directly and does not instantiate `AttackExecutor`.
- `AttackPolicyResult` is an immutable non-authoritative policy artifact. It contains no
  `security_failure` field.
- `PyRITMemoryScope` labels every PyRIT artifact with `agentsec_eval.run_id`, serializes the
  global-memory critical section, snapshots checked artifacts, clears its private database, and
  restores the exact prior `CentralMemory` binding.

## Stopping Semantics

| Progress state | PyRIT outcome | Policy stop reason | Next turn |
|---|---|---|---|
| `CONTINUE` | false score | budget exhaustion only | yes |
| `OBJECTIVE_ACHIEVED` | success | `objective_achieved` | no |
| `TERMINAL_BLOCKED` | failure | `terminal_blocked` | no |
| `INVALID_RUN` | failure | `invalid_run` | no |

Only objective achievement becomes PyRIT success. A terminal block is never converted to success
just to stop the native loop.

## Correlation and Trace

The JSON Target contract now forbids extras and blank durable IDs. Each response must match the
active project Session and have a strictly increasing project turn. The PromptTarget repeats those
checks at its own boundary and writes target requests, responses, tool calls, and tool results to
the policy's Canonical Trace emitter. The policy adds adversarial prompts, full trusted progress
decisions, and stopping events. Trace IDs and sequences remain unique and strictly increasing.

## Memory Limitation and Mitigation

PyRIT `0.14.0` resolves `CentralMemory` dynamically from multiple paths, and its public memory API
does not provide per-Run deletion. Its SQLite implementation is itself a singleton. Different
conversation IDs and labels are therefore not enough to claim lifecycle isolation.

M0-C creates a private SQLite singleton subclass backed by `:memory:` and holds a process-wide
lock from component construction through execution, a versioned full JSON snapshot of messages,
linked scores, and AttackResults, reset, and restoration. Two
async callers can be scheduled concurrently, but only one PyRIT policy executes in the critical
section at a time. This is intentionally serialized in-process execution. Real parallel policy
execution remains deferred to a future process/worker boundary.

PyRIT's SQLite JSON label query cannot match the required dotted key
`agentsec_eval.run_id`: it interprets the dot as a JSON path separator. The scope consequently
reads the already-exclusive database without that broken filter and rejects any message,
AttackResult, or score metadata whose Run label differs or is missing. The mandated dotted label is
still written to every Run artifact.

## Local Evidence

The M0-C test suite uses real PyRIT Strategy, PromptTarget, PromptNormalizer, `Score`,
`AttackResult`, and memory objects with deterministic project Target Sessions and adversarial
targets. It proves:

- all turns reuse the same project Session;
- objective success, terminal block, invalid Run, and exact budget semantics;
- sanitized `policy_feedback` reaches the adversarial target while private rationale does not;
- complete immutable turn records and Canonical Trace events;
- Target and adversarial errors return distinct policy error results, while the outer owner closes
  the Target Session;
- Memory cleanup and CentralMemory restoration after success, errors, and cancellation;
- concurrent callers retain isolated message, score, evidence, and AttackResult artifacts;
- PyRIT `FAILURE` with `TERMINAL_BLOCKED` can coexist with a deterministic test-only final
  assertion `security_failure=true` after a protected file is read before egress is blocked.

The baseline and final local command set is:

```bash
ruff check .
ruff format --check .
mypy
pytest -m "not docker"
pytest tests/unit/integrations/pyrit tests/integration/m0b tests/integration/m0c
pytest -m docker tests/integration/m0a
git diff --check
```

The CI workflow adds `m0c-pyrit` with `.[dev,pyrit]`, a strict `pyrit==0.14.0` version assertion,
explicit PyRIT/M0-C MyPy inputs, and focused unit/integration tests. `quality`, `m0a-docker`, and
`m0b-pyrit` stay independent.

The final local run on 2026-07-17 reported 54 core tests passed, 48 PyRIT/M0-B/M0-C tests passed,
and 2 M0-A Docker tests passed. Ruff, format checking, global MyPy, workflow YAML parsing, and
`git diff --check` also passed.

## Explicit Non-Goals

- No `BaseScenario`, `ScenarioCase`, `AttackSeed`, `ExecutableScenarioPack`, registry, importer,
  dataset, or Benchmark Adapter.
- No change to reference manifests, source locks, reference asset docs, scenario packs, datasets,
  or the M0-A Harness.
- No production Final Assertion Engine and no security verdict in Attack Policy output.
