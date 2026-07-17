# M0-A Inspect Execution Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove the Inspect AI `0.3.246` execution boundary with two isolated concurrent Samples,
three turns per Target Session, direct Docker evidence, and verified failure cleanup.

**Architecture:** Frozen Pydantic run/trace contracts map to Inspect Samples through a pure function.
The Target package depends on a project JSON transport Protocol; the execution package binds that
transport to Inspect's public Sandbox API and owns Store, Solver, Scorer, Task, and Eval lifecycle.

**Tech Stack:** Python 3.11, Hatchling, Pydantic 2, Inspect AI 0.3.246, Pytest, Docker Compose.

## Global Constraints

- Keep Hatchling and Python `>=3.11`.
- Runtime dependencies are exactly `inspect-ai==0.3.246` and `pydantic>=2,<3`.
- Never import `inspect_ai._*`; never copy Inspect source.
- No real model provider, API key, public egress, real credential, or sensitive file.
- No Campaign Controller, PyRIT, promptfoo, M0-B, M0-C, M1, persistence, or complete outcome model.
- One Run Spec maps to one Sample; one Sample opens one Session and uses one Compose Sandbox.
- All production behavior follows RED, GREEN, REFACTOR with recorded evidence.

---

### Task 1: Frozen domain contracts

**Files:**
- Create: `tests/unit/domain/test_models.py`
- Create: `src/agentsec_eval/domain/__init__.py`
- Create: `src/agentsec_eval/domain/models.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Produces: `TargetConfiguration`, `ExecutionScenarioSpec`, `AttackCandidate`, `ExecutionBudget`,
  `ExecutionRunSpec`, `CanonicalTraceEvent`, `validate_trace`.

- [ ] **Step 1: Add dependencies and failing model tests**

```python
def test_execution_run_spec_round_trips(run_spec: ExecutionRunSpec) -> None:
    restored = ExecutionRunSpec.model_validate_json(run_spec.model_dump_json())
    assert restored == run_spec

def test_execution_run_spec_is_frozen(run_spec: ExecutionRunSpec) -> None:
    with pytest.raises(ValidationError):
        run_spec.run_id = "changed"  # type: ignore[misc]
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/unit/domain/test_models.py -q`
Expected: collection fails because `agentsec_eval.domain` does not exist.

- [ ] **Step 3: Implement the six frozen models and trace validation**

```python
class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True)

class ExecutionRunSpec(FrozenModel):
    run_id: str
    target: TargetConfiguration
    scenario: ExecutionScenarioSpec
    attack_candidate: AttackCandidate
    budget: ExecutionBudget
    repetition_seed: int

def validate_trace(events: Sequence[CanonicalTraceEvent], run_id: str) -> None:
    if not events or any(event.run_id != run_id for event in events):
        raise ValueError("trace must be non-empty and match run_id")
    sequences = [event.sequence for event in events]
    if any(current >= following for current, following in pairwise(sequences)):
        raise ValueError("trace sequence must be strictly increasing")
```

- [ ] **Step 4: Verify GREEN and refactor**

Run: `pytest tests/unit/domain/test_models.py -q`
Expected: all domain tests pass.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml src/agentsec_eval/domain tests/unit/domain
git commit -m "feat: add frozen M0-A execution contracts"
```

### Task 2: Target protocols and adapter

**Files:**
- Create: `tests/unit/targets/test_http_session.py`
- Create: `tests/unit/targets/test_dependency_boundary.py`
- Create: `src/agentsec_eval/targets/__init__.py`
- Create: `src/agentsec_eval/targets/protocol.py`
- Create: `src/agentsec_eval/targets/http_session.py`

**Interfaces:**
- Consumes: `ExecutionRunSpec`.
- Produces: `TargetAdapter.open_session(run_spec)`, `TargetSession.send(message)`,
  `TargetSession.close()`, `TargetTurnResult`, `TargetToolCall`, `JsonRequestTransport`.

- [ ] **Step 1: Write failing adapter behavior and dependency tests**

```python
def test_target_session_reuses_session_id() -> None:
    transport = RecordingTransport()
    session = asyncio.run(JsonHttpTargetAdapter(transport).open_session(make_run_spec()))
    first = asyncio.run(session.send("one"))
    second = asyncio.run(session.send("two"))
    assert first.session_id == second.session_id == session.session_id

def test_targets_package_does_not_import_inspect() -> None:
    imports = imported_roots(Path("src/agentsec_eval/targets"))
    assert "inspect_ai" not in imports
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/unit/targets -q`
Expected: collection fails because the Target package does not exist.

- [ ] **Step 3: Implement project protocols and JSON session adapter**

```python
class TargetSession(Protocol):
    session_id: str
    async def send(self, message: str) -> TargetTurnResult: ...
    async def close(self) -> None: ...

class TargetAdapter(Protocol):
    async def open_session(self, run_spec: ExecutionRunSpec) -> TargetSession: ...

class JsonRequestTransport(Protocol):
    async def request(self, method: str, path: str, payload: dict[str, JsonValue], timeout: int) -> dict[str, JsonValue]: ...
```

The adapter creates `/sessions`, sends `/sessions/{id}/turns`, and idempotently closes
`/sessions/{id}` through this transport.

- [ ] **Step 4: Verify GREEN and refactor**

Run: `pytest tests/unit/targets -q`
Expected: adapter and dependency tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/agentsec_eval/targets tests/unit/targets
git commit -m "feat: define Inspect-independent target boundary"
```

### Task 3: Pure Inspect Sample mapping

**Files:**
- Create: `tests/unit/execution/test_inspect_backend.py`
- Create: `src/agentsec_eval/execution/__init__.py`
- Create: `src/agentsec_eval/execution/inspect_backend.py`

**Interfaces:**
- Consumes: `ExecutionRunSpec`.
- Produces: `execution_run_spec_to_sample(run_spec, peer_canaries=(), fail_after_session_open=False)`
  and `execution_run_spec_from_metadata(metadata)`.

- [ ] **Step 1: Write failing mapping tests**

```python
def test_run_spec_maps_to_one_sample(run_spec: ExecutionRunSpec) -> None:
    sample = execution_run_spec_to_sample(run_spec)
    assert sample.id == run_spec.run_id
    assert execution_run_spec_from_metadata(sample.metadata) == run_spec
    assert sample.metadata["agentsec_eval_schema_version"] == 1
```

- [ ] **Step 2: Verify RED**

Run: `pytest tests/unit/execution/test_inspect_backend.py -q`
Expected: import fails because the mapping module does not exist.

- [ ] **Step 3: Implement pure mapping**

```python
def execution_run_spec_to_sample(run_spec: ExecutionRunSpec, *, peer_canaries: Sequence[str] = (), fail_after_session_open: bool = False) -> Sample:
    return Sample(
        id=run_spec.run_id,
        input=f"{run_spec.scenario.user_task}\n\n{run_spec.attack_candidate.content}",
        metadata={
            "agentsec_eval_schema_version": 1,
            "execution_run_spec": run_spec.model_dump(mode="json"),
            "m0a_peer_canaries": list(peer_canaries),
            "m0a_fail_after_session_open": fail_after_session_open,
        },
    )
```

- [ ] **Step 4: Verify GREEN and refactor**

Run: `pytest tests/unit/execution/test_inspect_backend.py -q`
Expected: all mapping tests pass without starting Docker.

- [ ] **Step 5: Commit**

```bash
git add src/agentsec_eval/execution tests/unit/execution
git commit -m "feat: map project runs to Inspect samples"
```

### Task 4: Deterministic Compose Target

**Files:**
- Create: `tests/fixtures/m0a_inspect/compose.yaml`
- Create: `tests/fixtures/m0a_inspect/default/Dockerfile`
- Create: `tests/fixtures/m0a_inspect/default/client.py`
- Create: `tests/fixtures/m0a_inspect/target/Dockerfile`
- Create: `tests/fixtures/m0a_inspect/target/server.py`

**Interfaces:**
- Produces: standard-library HTTP endpoints `POST /sessions`,
  `POST /sessions/{id}/turns`, `GET /sessions/{id}`, `POST /sessions/{id}/close`.

- [ ] **Step 1: Write the fixture and validate Compose structure**

```yaml
services:
  default:
    build: ./default
    networks: [m0a_internal]
    labels:
      agentsec_eval.m0a.token: "${M0A_RESOURCE_TOKEN:-unset}"
  target:
    build: ./target
    networks: [m0a_internal]
    labels:
      agentsec_eval.m0a.token: "${M0A_RESOURCE_TOKEN:-unset}"
networks:
  m0a_internal:
    internal: true
    labels:
      agentsec_eval.m0a.token: "${M0A_RESOURCE_TOKEN:-unset}"
```

- [ ] **Step 2: Verify fixture configuration**

Run: `M0A_RESOURCE_TOKEN=plan-check docker compose -f tests/fixtures/m0a_inspect/compose.yaml config`
Expected: two services, no published ports, one internal labeled network.

- [ ] **Step 3: Commit**

```bash
git add tests/fixtures/m0a_inspect
git commit -m "test: add deterministic M0-A target fixture"
```

### Task 5: Inspect transport, Store, Solver, Scorer, and success path

**Files:**
- Create: `src/agentsec_eval/execution/m0a_harness.py`
- Modify: `src/agentsec_eval/execution/inspect_backend.py`
- Create: `tests/integration/m0a/conftest.py`
- Create: `tests/integration/m0a/test_success.py`

**Interfaces:**
- Produces: `build_m0a_task(run_specs, fail_run_ids=frozenset())`,
  `run_m0a_validation(run_specs, log_dir, fail_run_ids=frozenset())`, `m0a_solver()`, and
  `m0a_harness_validation_scorer()`.

- [ ] **Step 1: Write the failing two-Sample Docker test**

```python
@pytest.mark.docker
@pytest.mark.integration
@pytest.mark.timeout(180)
def test_two_samples_keep_sessions_stores_canaries_and_effects_isolated(tmp_path: Path) -> None:
    logs = run_m0a_validation(two_run_specs(), log_dir=tmp_path)
    samples = materialize_samples(logs)
    assert len(samples) == 2
    assert all(sample.scores["m0a_harness_validation_scorer"].value == CORRECT for sample in samples)
    assert len({sample.store["M0ARunState:session_id"] for sample in samples}) == 2
    assert len({sample.store["M0ARunState:sandbox_id"] for sample in samples}) == 2
```

- [ ] **Step 2: Verify RED**

Run: `pytest -m docker tests/integration/m0a/test_success.py -q`
Expected: import fails because `run_m0a_validation` does not exist.

- [ ] **Step 3: Implement the public Inspect boundary**

```python
class M0ARunState(StoreModel):
    run_id: str = ""
    session_id: str = ""
    sandbox_id: str = ""
    next_sequence: int = 1
    events: list[CanonicalTraceEvent] = Field(default_factory=list)

@solver
def m0a_solver() -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        del generate
        run_spec = execution_run_spec_from_metadata(state.metadata)
        runtime = store_as(M0ARunState)
        session: TargetSession | None = None
        try:
            transport = InspectSandboxJsonTransport("default")
            session = await JsonHttpTargetAdapter(transport).open_session(run_spec)
            append_event(runtime, run_spec, "session_opened", {"session_id": session.session_id})
            if state.metadata["m0a_fail_after_session_open"]:
                raise RuntimeError("M0-A injected failure after session open")
            for turn in range(1, 4):
                result = await session.send(f"turn-{turn}")
                record_turn(runtime, run_spec, turn, result)
            confirm_environment_effect(runtime, run_spec, session.session_id)
            return state
        except Exception as error:
            append_harness_error(runtime, run_spec, error)
            raise
        finally:
            if session is not None:
                await session.close()
                append_event(runtime, run_spec, "session_closed", {"session_id": session.session_id})
    return solve
```

The transport invokes `/opt/m0a/client.py` through `sandbox("default").exec`. The Scorer reconstructs
the Store model, scans `/effects` through `sandbox("target")`, and returns a structured `Score`.

- [ ] **Step 4: Verify GREEN and refactor**

Run: `pytest -m docker tests/integration/m0a/test_success.py -q`
Expected: two Samples pass with unique Session and Sandbox IDs and no peer Canary evidence.

- [ ] **Step 5: Commit**

```bash
git add src/agentsec_eval/execution tests/integration/m0a
git commit -m "feat: validate concurrent Inspect sample execution"
```

### Task 6: Failure cleanup

**Files:**
- Modify: `src/agentsec_eval/execution/m0a_harness.py`
- Create: `tests/integration/m0a/test_failure_cleanup.py`

**Interfaces:**
- Consumes: M0-A fault metadata and resource-token helpers.
- Produces: failed Eval evidence and bounded zero-delta Docker cleanup assertion.

- [ ] **Step 1: Write the failing cleanup test**

```python
@pytest.mark.docker
@pytest.mark.integration
@pytest.mark.timeout(180)
def test_solver_failure_closes_session_and_removes_new_resources(tmp_path: Path, resource_token: str) -> None:
    before = snapshot_resources(resource_token)
    logs = run_m0a_validation([make_run_spec("failure")], log_dir=tmp_path, fail_run_ids={"failure"})
    sample = materialize_samples(logs)[0]
    assert sample.error is not None
    assert {event["event_type"] for event in stored_events(sample)} >= {"harness_error", "session_closed"}
    wait_for_no_new_resources(resource_token, before, timeout_seconds=30)
```

- [ ] **Step 2: Verify RED**

Run: `pytest -m docker tests/integration/m0a/test_failure_cleanup.py -q`
Expected: the fault path or cleanup evidence assertion fails.

- [ ] **Step 3: Implement minimal failure handling**

Record `harness_error`, re-raise, close the Session in `finally`, record `session_closed`, and keep
`sandbox_cleanup=True`. Snapshot helpers filter only `agentsec_eval.m0a.token=<unique token>` and
compare post-run IDs against the baseline.

- [ ] **Step 4: Verify GREEN and broader Docker tests**

Run: `pytest -m docker tests/integration/m0a -q`
Expected: success and failure tests pass within their timeouts with no resource leak.

- [ ] **Step 5: Commit**

```bash
git add src/agentsec_eval/execution/m0a_harness.py tests/integration/m0a
git commit -m "test: prove Inspect failure cleanup"
```

### Task 7: CI and evidence documentation

**Files:**
- Modify: `pyproject.toml`
- Modify: `.github/workflows/ci.yml`
- Modify: `README.md`
- Modify: `docs/development/roadmap.md`
- Modify: `references/manifest.yaml`
- Create: `docs/development/m0-a-inspect-validation.md`
- Create: `docs/superpowers/tdd/2026-07-16-m0-a-inspect-execution-validation.md`

**Interfaces:**
- Produces: registered `docker`/`integration` markers, `pytest-timeout`, split CI, reproduction guide,
  final acceptance and TDD evidence.

- [ ] **Step 1: Register markers and split CI**

```yaml
jobs:
  quality:
    steps:
      - run: pytest -m "not docker"
  m0a-docker:
    steps:
      - run: docker version
      - run: docker compose version
      - run: pytest -m docker tests/integration/m0a
```

- [ ] **Step 2: Run all final gates**

```bash
ruff check .
ruff format --check .
mypy
pytest -m "not docker"
pytest -m docker tests/integration/m0a
```

Expected: zero failures and no Docker skip in the Docker-capable environment.

- [ ] **Step 3: Write evidence-based docs**

Record exact versions, public APIs, commands/results, five acceptance outcomes, limitations, and
`PASS` only after Step 2. Preserve M0-B/M0-C as not started.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml pyproject.toml README.md docs references
git commit -m "docs: record M0-A validation evidence"
```

### Task 8: Review and GitHub delivery

**Files:** all branch changes.

- [ ] **Step 1: Verify scope and clean diff**

Run: `git status && git diff --check && git diff --stat main...HEAD`
Expected: only M0-A contracts, execution boundary, fixtures, tests, CI, and docs.

- [ ] **Step 2: Run independent branch review and fix Important findings**

Check spec coverage, public Inspect imports, failure cleanup, deterministic/no-egress behavior, and
test evidence. Rerun affected tests after fixes.

- [ ] **Step 3: Final commit and push**

```bash
git add .
git commit -m "feat: validate Inspect AI execution model"
git push -u origin feat/m0-a-inspect-execution-validation
```

- [ ] **Step 4: Create Draft PR and wait for Actions**

Title: `M0-A: validate Inspect AI execution model`.
The body includes implementation, boundaries, acceptance matrix, exact commands/results, Inspect
version, limitations, Issue #3, and explicit M0-B/M0-C/M1 non-goals.
