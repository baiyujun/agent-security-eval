# M0-A Inspect Execution Validation Design

- Status: implemented and validated locally; Draft PR CI pending
- Date: 2026-07-16
- Issue: `#3 M0-A: validate Inspect AI execution model`
- Baseline: `main@f0680326314db766b6d5e1dea9dbf8742e70c5e7`
- Runtime: Inspect AI `0.3.246`, Pydantic `>=2,<3`, Python `>=3.11`

## Purpose

M0-A is a bounded vertical validation of the Inspect AI execution boundary. It must prove that a
small project-owned run contract can cross into Inspect, execute two concurrent Docker-backed
Samples without state leakage, reuse one external Target Session for three turns, produce
project-native trace evidence, and clean up resources after both success and failure.

M0-A is not the production execution backend and does not implement Campaign control, PyRIT,
promptfoo, a complete Final Assertion Engine, a complete outcome model, persistence, or M1. The
existing `experiments/inspect-execution-model/` code remains a throwaway research spike. The formal
implementation will use the public APIs it validated but will not import, rename, or promote that
code.

## Approaches Considered

### A. Inspect-aware concrete Target Adapter

The Target protocols remain project-owned, but their concrete implementation directly calls
`inspect_ai.util.sandbox()`.

- Advantage: fewest moving parts.
- Rejected because: the Target package would know the execution runtime and would be hard to test or
  reuse without an active Inspect Sample.

### B. Project Target protocols with an injected transport

The Target package defines `TargetAdapter`, `TargetSession`, result types, and a narrow asynchronous
transport protocol. It contains no Inspect import. The execution package supplies a transport backed
by Inspect's public Sample-scoped Sandbox API.

- Advantage: demonstrates the required type and dependency boundary while keeping transport details
  testable and runtime-local.
- Cost: one additional protocol and conversion step.
- Decision: adopt this approach.

### C. Solver-owned HTTP protocol

The Solver invokes a fixture client directly and performs all session/protocol conversion itself.

- Advantage: smallest initial code volume.
- Rejected because: it bypasses `TargetAdapter`, mixes Inspect lifecycle with Target protocol logic,
  and makes future adapters copy the same session rules.

## Ownership Boundaries

```text
Frozen project run contracts
  -> execution_run_spec_to_sample
  -> Inspect Sample metadata (versioned JSON)
  -> custom M0-A Solver
       -> Inspect-backed transport (execution package)
       -> project TargetAdapter / one TargetSession (targets package)
       -> Sample-scoped typed Store (execution package)
       -> project CanonicalTraceEvent records
       -> direct Sandbox environment-effect confirmation
  -> harness-only M0-A Scorer
       -> typed Store trace checks
       -> direct target-Sandbox file checks
  -> Inspect EvalLog
```

- `domain` owns durable, Inspect-independent data and trace invariants.
- `targets` owns session lifecycle and Target response normalization. It imports no Inspect type.
- `execution` owns Inspect mapping, typed Store, Sandbox transport binding, Solver, Scorer, Task, and
  Eval lifecycle.
- `tests/fixtures/m0a_inspect` owns the deterministic Compose environment and its HTTP protocol
  executable. It is not packaged as product runtime code.
- The M0-A Scorer validates the harness only. It is not formal security truth.

## Project-Owned Contracts

All models use Pydantic v2 with `ConfigDict(frozen=True)`. They serialize with
`model_dump_json()` and restore with `model_validate_json()`.

`TargetConfiguration` contains `target_id`, `adapter`, and `version`.

`ScenarioSpec` contains `scenario_id`, `user_task`, and a Sample-unique `canary`.

`AttackCandidate` contains `candidate_id` and `content`.

`ExecutionBudget` contains positive `max_turns` and `timeout_seconds` values. The M0-A Task rejects a
budget with fewer than three turns.

`ExecutionRunSpec` contains `run_id`, `target`, `scenario`, `attack_candidate`, `budget`, and
`repetition_seed`. The complete model is immutable and Inspect-independent.

`CanonicalTraceEvent` contains `event_id`, `run_id`, `sequence`, `event_type`, `source`,
`observation_strength`, and a JSON-only `payload`. Supported event types are `session_opened`,
`target_request`, `target_response`, `tool_call`, `tool_result`, `environment_effect`,
`session_closed`, and `harness_error`. Supported observation strengths are `target_reported`,
`harness_observed`, and `environment_confirmed`.

A project helper validates that a trace is non-empty, every event has the expected `run_id`, event
IDs are unique, and sequences are strictly increasing. The Solver emits contiguous sequences
starting at one.

## Target Boundary

`TargetAdapter.open_session(run_spec)` returns one `TargetSession`. `TargetSession.send(message)`
returns a project-native `TargetTurnResult`; `TargetSession.close()` is idempotent. No protocol
signature contains an Inspect type.

The Target package also defines a narrow asynchronous JSON request transport consumed by the HTTP
session adapter. The execution package binds it to
`sandbox("default").exec(["python", "/opt/m0a/client.py"], input=...)`. The client runs inside the
default Sandbox service, uses Python's standard-library HTTP client, and contacts `target:8080` over
the internal Compose network. There is no host HTTP request and no host port binding.

The adapter opens exactly one Session, retains its `session_id`, sends every turn through that
Session, converts optional tool-call/tool-result records, and closes the same Session in the
Solver's `finally` block.

## Run Spec to Sample Mapping

`execution_run_spec_to_sample()` is a pure mapping function:

- one call returns exactly one `Sample`;
- `Sample.id` equals `ExecutionRunSpec.run_id`;
- the input contains the user task and deterministic candidate content;
- metadata contains a schema version and the complete JSON-mode Run Spec;
- metadata may contain M0-A-only peer-canary and fault-injection controls outside the Run Spec;
- the function does not start evaluation, create a Sandbox, or open a Session.

The Solver reconstructs the model only from `TaskState.metadata` and verifies that the restored
`run_id` matches `TaskState.sample_id`.

## Sample-Scoped State and Trace Flow

The execution package defines an M0-A-only `StoreModel` with `run_id`, `session_id`, `sandbox_id`,
`next_sequence`, and `events`. This type is runtime-local and never enters `domain` or `targets`.
Each Sample receives its own Inspect Store automatically.

The Solver performs this sequence:

1. Restore and validate the Run Spec.
2. Capture the public `sandbox("default").connection().container` identity.
3. Create one TargetAdapter and open one TargetSession.
4. Record `session_opened`.
5. If failure injection is enabled for this Sample, raise after Session creation.
6. Send three deterministic turns through the same Session.
7. Record one `target_request` and one `target_response` per turn.
8. Convert the second-turn simulated tool call and result into separate canonical events.
9. On the third turn, read the reported effect path directly from `sandbox("target")` and validate
   its `run_id`, `session_id`, and canary before recording `environment_effect` with
   `environment_confirmed` strength.
10. On any exception, record `harness_error` and re-raise.
11. In `finally`, close the opened Session and record `session_closed` when state is available.

The Store updates the event list by assignment rather than in-place mutation so Inspect records
each state transition. No module-level mutable state is used.

## Deterministic Docker Compose Fixture

`tests/fixtures/m0a_inspect/compose.yaml` defines two services on one `internal: true` network:

- `default`: a long-running Python 3.11 container containing only the standard-library client.
- `target`: a Python 3.11 standard-library HTTP server containing the session state and effect files.

The Compose file publishes no host ports. Both services and the network carry an
`agentsec_eval.m0a.token` label interpolated from a test-unique `M0A_RESOURCE_TOKEN`.

The Target HTTP API supports Session creation, turn submission, Session state query, and idempotent
close. Turn one returns initialized state. Turn two returns a simulated `read_file` tool call and
tool result. Turn three writes one JSON effect file inside the target container and returns its path.
The file contains the current `run_id`, `session_id`, and canary. State is keyed by `session_id` and
exists only inside that Sample's target container.

## Harness Scorer

`m0a_harness_validation_scorer` returns `CORRECT` only when all checks pass. `Score.metadata`
contains a named boolean result and detail for every check:

- Sample ID, metadata Run ID, Store Run ID, and all event Run IDs match;
- exactly one Session ID exists;
- at least three target requests and responses exist;
- tool-call and tool-result events exist;
- event sequences are strictly increasing;
- the target-Sandbox effect file exists and matches the current Run ID, Session ID, and canary;
- a direct target-Sandbox scan of every effect file contains no peer Sample canary;
- environment evidence uses `environment_confirmed` strength; and
- every recorded turn uses the captured Sample Sandbox identity.

The Scorer reads the effect file through `sandbox("target").read_file()`. A Target response that only
claims an effect occurred cannot satisfy the check.

## Failure and Cleanup

Fault injection is M0-A execution metadata, not a domain field. It raises immediately after
`session_opened`, exercises `harness_error`, rethrows to Inspect, and still invokes Session close in
`finally`.

`run_m0a_validation()` always requests `sandbox_cleanup=True`. The integration test records the
sets of container and network IDs carrying its unique resource-token label before evaluation. After
the failing Eval returns, it polls for a bounded interval until the set difference is empty. It does
not prune Docker, inspect unrelated resources, or remove resources present in the baseline. No
remaining labeled target container also proves that the Fake Target process is gone.

## Automated Verification

Unit tests cover frozen/round-trip models, trace invariants, one-to-one Sample mapping, metadata
recovery, Sample ID equality, and the absence of `inspect_ai` imports in the Target package.

The successful Docker integration test runs two Run Specs in one Task with `max_samples=2` and the
official `mockllm/model`. It verifies two successful Eval samples, different Session and Sandbox
identities, three turns per Sample, separate Stores/canaries/effect files, passing structured scores,
and discoverable EvalLog results.

The failure integration test uses one fault-injected Sample, a bounded test timeout, and a unique
resource token. It verifies an Inspect error result, `harness_error` and `session_closed` events in
the failed Sample's persisted Store, and zero newly leaked labeled containers or networks.

Pytest markers `docker` and `integration` are registered. Local environments may skip Docker tests
only with a concrete Docker-unavailable reason. The CI Docker job first runs `docker version` and
`docker compose version`; either command failing fails the job rather than skipping M0-A.

CI retains Ruff, formatting, MyPy, and unit tests, and adds a dedicated M0-A Docker job. Neither job
uses API keys or a real model.

## Documentation and Completion Rule

`docs/development/m0-a-inspect-validation.md` records the exact public APIs, version, mapping,
Store/Sandbox/session lifecycle, cleanup approach, reproduction commands, limitations, and five-item
acceptance matrix. It may state `PASS` only after the Docker success and failure tests both run and
all repository gates pass.

README gains the M0-A commands. The roadmap records only M0-A's observed status. The manifest pins
the released Inspect dependency evidence without changing unrelated reference decisions.

M0-A is complete only when all of these commands pass from a clean branch and the Draft PR's Docker
job passes on a fresh GitHub Actions runner:

```bash
ruff check .
ruff format --check .
mypy
pytest -m "not docker"
pytest -m docker tests/integration/m0a
```
