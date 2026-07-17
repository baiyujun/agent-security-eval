# Hai TDD: M0-C PyRIT Attack Policy Embedding

## Target Behavior

One project Run drives a pinned PyRIT `0.14.0` red-teaming policy through one existing Target
Session. The project, rather than PyRIT's boolean loop, decides all terminal states, captures
trusted trace/evidence, and serializes global-memory use without producing final security truth.

## RED

- **Test added**: `tests/unit/targets/test_http_session.py` correlation and schema cases.
- **Behavior asserted**: Target models forbid extras and blank IDs; response Session IDs match and
  turns strictly increase.
- **Command**: `pytest tests/unit/targets/test_http_session.py -q`
- **Observed failure**: 9 failures; unknown fields, blank IDs, foreign Session IDs, and duplicate or
  decreasing turns were accepted.
- **Failure is correct because**: the initial contract used only frozen models and returned parsed
  Target responses without correlation checks.

- **Test added**: `tests/unit/assertions/test_progress.py` state/stage/evidence matrix.
- **Behavior asserted**: achieved requires EFFECT plus evidence, continue and blocked cannot use
  EFFECT, invalid requires NONE, and evidence IDs are unique.
- **Command**: `pytest tests/unit/assertions/test_progress.py -q`
- **Observed failure**: 5 failures; every added invalid combination constructed successfully.
- **Failure is correct because**: the existing validator only required evidence for achieved state.

- **Test added**: `tests/unit/integrations/pyrit/test_prompt_target.py`.
- **Behavior asserted**: real PyRIT public PromptTarget sends reuse a Session, preserve lineage,
  write Target trace data, and wrap Target boundary errors.
- **Command**: `pytest tests/unit/integrations/pyrit/test_prompt_target.py -q`
- **Observed failure**: collection failed because `TargetSessionPromptTarget` did not exist.
- **Failure is correct because**: there was no project PromptTarget adapter before M0-C.

- **Test added**: `tests/unit/integrations/pyrit/test_result.py`.
- **Behavior asserted**: policy results are immutable, round-trip, have coherent stop/turn state,
  and cannot contain a final security verdict.
- **Command**: `pytest tests/unit/integrations/pyrit/test_result.py -q`
- **Observed failure**: collection failed because the result contracts did not exist.
- **Failure is correct because**: M0-B intentionally stopped before policy result ownership.

- **Test added**: `tests/unit/integrations/pyrit/test_memory.py`.
- **Behavior asserted**: real PyRIT messages, scores, and AttackResults are Run-labeled, cleaned,
  restored, and isolated for concurrent callers, errors, and cancellation.
- **Command**: `pytest tests/unit/integrations/pyrit/test_memory.py -q`
- **Observed failure**: collection failed because `PyRITMemoryScope` did not exist.
- **Failure is correct because**: M0-B made no process-global CentralMemory lifecycle claim.

- **Test added**: `tests/integration/m0c/test_policy.py`.
- **Behavior asserted**: immediate project-terminal stops, exact budget, Session reuse, sanitized
  feedback, complete trace, and classified Target/adversarial errors.
- **Command**: `pytest tests/integration/m0c/test_policy.py -q`
- **Observed failure**: collection failed because `PyRITAttackPolicy` did not exist.
- **Failure is correct because**: the policy loop is the M0-C deliverable.

## GREEN

- **Minimal implementation**: added strict project Target and ProgressDecision validation; added
  `TargetSessionPromptTarget`, immutable policy value contracts, a serialized resettable
  `PyRITMemoryScope`, and a private `RedTeamingAttack` subclass that overrides only
  `_perform_async()`. The public policy creates the components inside the scope and maps its
  persisted PyRIT result to `AttackPolicyResult`.
- **Command**: `pytest tests/unit/targets/test_http_session.py tests/unit/assertions/test_progress.py tests/unit/integrations/pyrit tests/integration/m0b tests/integration/m0c -q`
- **Observed pass**: the final separated gates reported 54 core tests passed, 53 PyRIT/M0-B/M0-C
  tests passed, and 2 M0-A Docker tests passed.

## REFACTOR

- **Refactor done**: yes.
- **Change**: replaced PyRIT's deprecated response-construction helper with
  `MessagePiece.copy_lineage_from()` in the project PromptTarget, keeping equivalent lineage while
  eliminating adapter-owned warnings. Added a typed canonical trace emitter and kept supporting
  turn/result values subordinate to the four public runtime boundaries.
- **Command after refactor**: `pytest tests/unit/integrations/pyrit tests/integration/m0c -q`
- **Observed result**: all tests passed without project-owned warnings.

## Debugging Evidence

The first Memory Scope green run found one unexpected failure: an `AttackResult` stored with
`{"agentsec_eval.run_id": "run-1"}` was returned by an unfiltered PyRIT query but not by
`get_attack_results(labels={"agentsec_eval.run_id": "run-1"})`. A direct reproduction showed
`all_count=1` and `filtered_count=0`; a control key without a dot filtered successfully. The cause
is PyRIT SQLite JSON-path interpretation of the required dotted key. The scope now reads only its
exclusive resettable database and validates the exact required label in Python before cleanup.

Two additional review-driven RED cycles hardened the completed boundary:

- A PromptTarget built against foreign CentralMemory was accepted and completed a policy Run. The
  policy now verifies that the adversarial factory created its target inside the active scope; the
  focused RED changed from `terminal_blocked` to the expected `policy_error` after GREEN.
- The first memory artifact exposed only counts and IDs, so its `pyrit_result_ref` was not
  auditable after database reset. The artifact now includes versioned full JSON MessagePiece/Score
  and AttackResult snapshots, and concurrent tests assert Run-specific message content does not
  cross artifacts.

Two PR #8 review corrections added further test-first evidence:

- **Test added**:
  `test_policy_uses_explicit_attack_objective_for_adversarial_system_prompt`.
- **Behavior asserted**: benign `user_task`, attacker `attack_objective`, and concrete attack seed
  are distinct, and only the explicit attacker objective drives PyRIT's adversarial system prompt.
- **RED command**:
  `pytest tests/integration/m0c/test_policy.py::test_policy_uses_explicit_attack_objective_for_adversarial_system_prompt -q`.
- **Observed RED**: one failure with `PyRITAttackPolicy.run() got an unexpected keyword argument
  'attack_objective'`.
- **Failure is correct because**: the Policy boundary had no way to receive the attacker objective
  and substituted the normal user task.
- **Minimal GREEN implementation**: added required `attack_objective: str`, passed its normalized
  value to PyRIT `execute_async(objective=...)`, and rejected blank values.
- **GREEN commands**: the focused objective test passed `1 passed`; the separate blank-objective
  RED first reported `2 failed`, then passed as `3 passed` with the objective test after validation;
  the complete policy file passed as `12 passed`.
- **Refactor**: the shared policy fixture now supplies a semantically distinct default objective;
  no domain or Benchmark model was added.

- **Test added**: `test_memory_scope_rejects_scores_without_current_run_id` with missing metadata,
  empty metadata, and foreign Run ID cases.
- **Behavior asserted**: every captured Score must carry the current Run ID before its audit
  artifact is accepted.
- **RED command**:
  `pytest tests/unit/integrations/pyrit/test_memory.py::test_memory_scope_rejects_scores_without_current_run_id -q`.
- **Observed RED**: `2 failed, 1 passed`; missing and empty metadata were accepted while the foreign
  Run ID was already rejected.
- **Failure is correct because**: the original condition checked a Score only when its metadata was
  truthy.
- **Minimal GREEN implementation**: treat absent metadata or any `run_id` unequal to the active Run
  as invalid.
- **GREEN command**: `pytest tests/unit/integrations/pyrit/test_memory.py -q`.
- **Observed GREEN**: `8 passed`.
- **Refactor**: no further refactor was needed; the validation remains one explicit list
  comprehension alongside message and AttackResult ownership checks.

## Next Behavior

No additional review-requested M0-C runtime behavior remains. The complete local verification
matrix is green; remaining delivery work is the protected-surface diff review, push, and GitHub
Actions confirmation.
