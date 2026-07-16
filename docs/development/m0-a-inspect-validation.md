# M0-A Inspect AI Execution Validation

## Verdict

**PASS for the bounded M0-A execution-model validation.** On 2026-07-16, the static, non-Docker,
successful Docker, and injected-failure Docker gates passed locally and on Draft PR #4's fresh
GitHub Actions runner.

This verdict does not mean the security evaluation system, production execution backend, Final
Assertion Engine, M0-B, M0-C, or M1 is complete.

## Purpose and Boundary

M0-A validates that a minimal project-owned execution contract can cross into Inspect AI, execute
concurrent isolated Samples, interact with a deterministic external Target for three Turns, retain
project-native trace evidence, directly confirm a Sandbox effect, and clean up Docker resources on
failure.

The formal code lives in three boundaries:

- `agentsec_eval.domain`: frozen Inspect-independent Run and trace contracts;
- `agentsec_eval.targets`: Inspect-independent Target protocols and JSON Session adapter; and
- `agentsec_eval.execution`: Inspect mapping, Sandbox transport, Store, Solver, Scorer, Task, and
  Eval lifecycle.

`experiments/inspect-execution-model/` remains a throwaway research spike. It was neither renamed nor
promoted into the formal implementation.

## Fixed Runtime and Public APIs

- Python: `>=3.11`
- Inspect AI: exactly `0.3.246`
- Pydantic: `>=2,<3`
- Model: Inspect's no-key `mockllm/model`

The implementation imports only public Inspect modules and uses these public APIs:

- `inspect_ai.Task` and `inspect_ai.eval`;
- `inspect_ai.dataset.Sample` and `MemoryDataset`;
- `inspect_ai.solver.solver`, `Solver`, `TaskState`, and `Generate`;
- `inspect_ai.scorer.scorer`, `Scorer`, `Score`, `Target`, `CORRECT`, and `INCORRECT`; and
- `inspect_ai.util.sandbox`, `StoreModel`, and `store_as`, including the returned Sandbox
  environment's asynchronous `exec()`, `read_file()`, and `connection()` methods.

No `inspect_ai._*` module is imported, and no Inspect source is copied.

## Run Spec to Sample Mapping

`execution_run_spec_to_sample()` is a pure one-to-one mapping:

- `Sample.id` equals `ExecutionRunSpec.run_id`;
- `Sample.input` contains the scenario task and deterministic candidate content;
- `Sample.metadata.agentsec_eval_schema_version` is `1`;
- the complete Run Spec is stored as JSON-mode metadata and can be reconstructed without a closure or
  global variable; and
- peer-canary and fault-injection controls remain M0-A execution metadata, outside the domain model.

The mapping creates no Session, Sandbox, Task, or Eval.

## Session, Store, and Trace Lifecycle

For each Sample, the Solver restores the Run Spec from metadata, obtains the Sample's public Docker
container identity, and initializes one Sample-scoped `M0ARunState` Store model. It then opens one
project `TargetSession`, retains its `session_id`, and sends three deterministic messages through the
same Session and default Sandbox.

The Store persists `run_id`, `session_id`, `sandbox_id`, seven direct Sandbox observations, the next
sequence, and frozen `CanonicalTraceEvent` values. The Solver calls the public Sandbox
`connection()` once initially and immediately before and after each Turn. Events use unique IDs and
strictly increasing sequences. The second Turn's simulated `read_file` call and result become
separate `tool_call` and `tool_result` events. Every Target request and response records the identity
observed at that point.

The Session close request is idempotent. The Solver closes it in `finally` and records
`session_closed` after the close request succeeds.

## Docker Target and Environment Evidence

`tests/fixtures/m0a_inspect/compose.yaml` contains `default` and `target` services with no published
host ports. Both services run on one `internal: true` network and carry a test-unique
`agentsec_eval.m0a.token` label. The Target is a Python standard-library HTTP server; no Flask,
FastAPI, API key, real credential, or external model is used.

Turn 3 writes one JSON effect file containing the current `run_id`, `session_id`, and Canary. The
Solver and Scorer read that file from `sandbox("target")`; the Target's text response alone is not
accepted as confirmation. The Scorer also scans every effect file in the current Target Sandbox and
rejects a peer Sample's Canary.

The Target writes effects to its ephemeral writable container layer. During validation, the file
existed inside a `tmpfs` mount, but Inspect `0.3.246` Docker `read_file()` uses Compose copy, and this
Docker engine could not copy from that mount. Removing the mount preserved ephemeral container
cleanup while allowing the documented public API to collect evidence.

## Harness Scorer

`m0a_harness_validation_scorer` is validation logic for this Harness, not formal security truth. It
returns `CORRECT` only when structured checks confirm:

- Sample, metadata, Store, and Trace Run IDs agree;
- exactly one Session ID and one Sample Sandbox identity are used;
- at least three Target requests and responses exist;
- `tool_call` and `tool_result` events exist;
- trace IDs and sequences satisfy project invariants;
- one `environment_confirmed` event exists;
- the directly read effect matches the current Run ID, Session ID, and Canary; and
- a direct Target Sandbox scan contains no peer Canary.

Every required check is recorded under `Score.metadata.checks` with a boolean result and detail. The
integration test asserts the exact check-name set. Effect reads, JSON decoding, metadata validation,
and Target scans become named failed checks and `INCORRECT`; they do not escape as Scorer errors.

## Failure and Cleanup

For selected Run IDs, M0-A metadata injects a `RuntimeError` immediately after `session_opened`. One
failed Sample proves the Solver records `harness_error`, rethrows to Inspect, closes the Target
Session in `finally`, and persists `session_closed`. A second Sample injects a transport error after
the Target has processed close; the Store records a second `harness_error` with
`phase=session_close`, while the EvalSample retains the original Solver error.

`run_m0a_validation()` always passes `sandbox_cleanup=True`. During Eval, a monitor must observe at
least four token-labeled service containers and two labeled networks for the two failed Samples.
After Eval, the test polls for at most 30 seconds until those exact new IDs disappear. It never
invokes `docker system prune`, removes no baseline resource, and leaves no labeled Target container
or process.

## Five-Item Acceptance Matrix

| Required proof | Result | Automated evidence |
|---|---|---|
| One project Run Spec maps to one Inspect Sample | PASS | Unit mapping and metadata-recovery tests |
| A custom Solver completes at least three external Target Turns | PASS | Overlapping two-Sample Docker success test |
| Three Turns reuse one logical Session and one Sample Sandbox | PASS | One Session plus seven direct Sandbox observations per Sample |
| Target traffic, tool events, environment evidence, and Scorer correlate to one Run ID | PASS | Canonical trace and structured Score checks |
| Solver failure cleans Target Session and Inspect Docker resources | PASS | Normal-close and close-error Stores plus observed-resource disappearance |

## Reproduction

Install the project on Python 3.11 or newer:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

Run all gates:

```bash
ruff check .
ruff format --check .
mypy
pytest -m "not docker"
docker version
docker compose version
pytest -m docker tests/integration/m0a
```

Observed local results on 2026-07-16 before delivery:

- Ruff check: passed;
- Ruff format check: passed;
- MyPy: passed;
- non-Docker Pytest: `24 passed, 2 deselected`;
- Docker Pytest: `2 passed in 57.06s`; and
- M0-A labeled container/network sets: empty before and after the combined Docker run.

Draft PR #4 GitHub Actions results:

- `quality`: passed in 46 seconds; and
- `m0a-docker`: passed in 1 minute 39 seconds.

## Known Limitations

- M0-A is a validation Harness, not a production execution backend or security oracle.
- It uses a deterministic Fake Target and Inspect mock model, not a real Agent or provider.
- It validates Inspect AI `0.3.246`; beta API and EvalLog schema changes require contract retesting.
- It validates normal completion, post-Session-open failure, and a post-close transport error, not
  cancellation, retry, resume, or host termination.
- Cleanup assertions cover token-labeled containers and networks. The fixture declares no volumes;
  Docker image layers and build cache are outside the Sample runtime-resource assertion.
- The Compose fixture is resolved from a source checkout and is not packaged as a distributable
  production asset.
- No Campaign Controller, PyRIT, promptfoo, corpus, persistence, complete outcome model, M0-B, M0-C,
  or M1 behavior is implemented.
