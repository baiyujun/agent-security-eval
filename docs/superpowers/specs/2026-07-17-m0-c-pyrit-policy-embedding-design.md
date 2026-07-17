# M0-C PyRIT Attack Policy Embedding Design

## Scope

M0-C validates a project-controlled, single-Run attack policy over PyRIT `0.14.0`:

```text
ExecutionRunSpec + open TargetSession
    -> TargetSessionPromptTarget
    -> project-controlled PyRIT turn loop
    -> AssertionBackedPyRITScorer
    -> AttackPolicyResult
```

The policy result is an attack-execution artifact, not final security truth. A deterministic test
assertion may therefore report `security_failure=true` when PyRIT reports `FAILURE`, including a
late-block case where the protected effect occurred before outbound communication was blocked.

The only public runtime boundaries added by this milestone are `TargetSessionPromptTarget`,
`PyRITAttackPolicy`, `AttackPolicyResult`, and `PyRITMemoryScope`. Supporting enums and immutable
turn records remain subordinate value types. M0-C does not add scenario assets, a Campaign
Controller, a production Execution Backend, a production Final Assertion Engine, or `RunOutcome`.

## Dependency Audit

The design is pinned to observed PyRIT `0.14.0` behavior:

- `PromptTarget.send_prompt_async()` is final; target adapters implement
  `_send_prompt_to_target_async()`.
- `Strategy.execute_with_context_async()` guarantees setup and teardown around `_perform_async()`.
- `RedTeamingAttack._perform_async()` is the intended protected execution extension point.
- The native loop stops early only when `bool(last_score.get_value())` is true. It cannot represent
  `False` plus terminal for `TERMINAL_BLOCKED` or `INVALID_RUN`.
- `PromptTarget`, `PromptNormalizer`, `ConversationManager`, the default Attack Strategy event
  handler, and some scorer paths all consult process-global `CentralMemory`; the scorer property
  resolves it dynamically.
- `MemoryInterface` supports Run-label queries and database reset, but exposes no public per-Run
  deletion API. `SQLiteMemory` is itself a process singleton.

These facts rule out both native stopping and conversation-ID-only memory claims.

## Chosen Approach

### Policy loop

`PyRITAttackPolicy` constructs a private subclass of the pinned `RedTeamingAttack`. The subclass
reuses PyRIT setup, adversarial prompt generation, objective-target sending, scoring, event
persistence, and lifecycle handling, but replaces `_perform_async()` with the project loop:

```text
generate adversarial prompt
-> send through TargetSessionPromptTarget
-> score through AssertionBackedPyRITScorer
-> recover the complete ProgressDecision from trusted score metadata
-> record the turn
-> stop on any project-terminal state or exact max_turns
```

Only `OBJECTIVE_ACHIEVED` produces PyRIT `AttackOutcome.SUCCESS`. `TERMINAL_BLOCKED`,
`INVALID_RUN`, and budget exhaustion produce `FAILURE`; operational exceptions produce PyRIT
`ERROR` through the existing Strategy event lifecycle. The policy never uses `AttackExecutor` or a
second controller.

The adversarial model receives PyRIT's `score_rationale`, which M0-B already restricts to
`ProgressDecision.policy_feedback`. Complete score metadata and `internal_rationale` remain trusted
artifacts and are never formatted into the adversarial prompt.

### Memory lifecycle

`PyRITMemoryScope` owns one process-wide critical section. On entry it:

1. acquires a cancellation-safe process lock;
2. saves the current `CentralMemory` binding;
3. resets a private in-memory SQLite subclass used only by this integration;
4. binds that empty memory as `CentralMemory`;
5. exposes the mandatory label `agentsec_eval.run_id=<run_id>`.

All PyRIT components are constructed and executed inside that scope. On exit it snapshots and
validates messages, linked scores, and AttackResults, resets the private database, restores the
previous central binding exactly, and releases the lock even on Target, adversarial, scorer,
policy, or cancellation errors.

This safely accepts concurrent callers, but serializes the PyRIT policy portion in one process.
M0-C does not claim parallel PyRIT policy execution. True parallel execution is deferred until a
worker/process boundary can carry a real Target Session and trace contract without relying on the
global singleton.

## Rejected Alternatives

| Approach | Decision | Reason |
|---|---|---|
| Native `RedTeamingAttack` with current scorer | reject | False terminal states run to the budget and corrupt stopping semantics. |
| Fully custom loop over low-level PyRIT pieces | reject | Duplicates setup, prompt normalization, persistence, and error lifecycle while coupling to more internals. |
| Distinct conversation IDs plus Run labels | reject | Supports filtering, not lifecycle isolation or cleanup; dynamic global-memory reads can still cross Runs. |
| Swap separate CentralMemory instances concurrently | reject | Process-global rebinding races between coroutines and threads. |
| One OS process per Run | defer | Strongest parallel isolation, but transporting a live Target Session is outside the bounded M0-C proof. |

## Target Boundary

`TargetSessionPromptTarget` binds one non-empty Run ID and one already-open project
`TargetSession`. It declares native multi-turn text support so PyRIT keeps one objective
conversation. Every send:

- reads exactly one text request from the normalized conversation;
- calls the same `TargetSession.send()` object;
- verifies the returned project Session ID;
- verifies a strictly increasing positive project turn;
- converts the project response to a lineage-preserving PyRIT assistant message;
- records objective conversation ID, project Session ID, request, response, tool calls, and effects
  through the policy's Canonical Trace emitter.

It never opens or closes the Target Session. The owning execution layer retains lifecycle
responsibility. The existing JSON HTTP session repeats correlation checks at the transport
boundary, rejects unknown fields, and rejects blank durable IDs.

## Project Contracts

`ProgressDecision` is hardened before policy use:

- `OBJECTIVE_ACHIEVED` requires `EFFECT` and at least one unique evidence ID.
- `CONTINUE` cannot use `EFFECT`.
- `INVALID_RUN` requires `NONE`.
- `TERMINAL_BLOCKED` cannot use `EFFECT`; late block may still use `EXECUTED`.

`AttackPolicyResult` is immutable, rejects extras, and contains Run identity, policy identity,
turn count, stop reason, final progress decision when one exists, objective and adversarial
conversation IDs, complete immutable turn records, PyRIT outcome, and stable references to the
persisted PyRIT result and captured memory artifact. It intentionally has no authoritative
`security_failure` field.

The stop reasons are `objective_achieved`, `terminal_blocked`, `invalid_run`, `budget_exhausted`,
`target_error`, `policy_error`, and `cancelled`. Cancellation still propagates to the caller after
cleanup; the vocabulary is reserved for future orchestration without inventing a `RunOutcome`.

## Trace and Artifacts

The policy accepts a mutable sequence of `CanonicalTraceEvent`. It validates any existing events
against the Run and continues after the last sequence. M0-C adds event vocabulary for adversarial
prompts, progress decisions, and policy stopping while reusing target request/response/tool/effect
events. Event IDs and sequences remain unique and strictly increasing.

Each turn record contains the adversarial prompt, Target response, project turn, public score
value and rationale, and full trusted `ProgressDecision`. The memory artifact records counts,
conversation IDs, score IDs, AttackResult IDs, and the mandatory Run label before the backing
database is cleared.

## Error Handling

- Correlation failures are Target errors and stop the policy without producing another turn.
- A Target exception is classified as `target_error`; other wrapped strategy failures are
  `policy_error`.
- PyRIT's lifecycle persists an `ERROR` AttackResult before its wrapped exception reaches the
  policy.
- Memory cleanup and CentralMemory restoration run in `finally` paths and do not depend on a
  successful AttackResult.
- Target Session closure remains the outer execution owner's job and is tested with a fixture that
  closes the Session around policy execution, including errors.

## Acceptance Proof

Deterministic tests use real PyRIT `0.14.0` message, scorer, strategy, memory, and AttackResult
paths with fake project Target Sessions and fake adversarial PromptTargets. They prove:

- same project Session on every turn and correlated responses;
- immediate stop for all three terminal project states;
- exact budget exhaustion;
- only sanitized policy feedback reaches the adversarial target;
- complete turn and Canonical Trace records;
- memory and Session cleanup on success, Target errors, adversarial errors, and concurrent calls;
- messages, scores, evidence, and AttackResults never cross Run labels;
- PyRIT `FAILURE` plus `TERMINAL_BLOCKED` can coexist with deterministic
  `security_failure=true` final evidence.

## Protected Surfaces

M0-C does not modify `references/manifest.yaml`, `references/source-locks/`,
`references/import-selection/`, `docs/reference-assets/`, scenario packs, datasets, or the M0-A
Harness. It consumes `ExecutionRunSpec`, `ExecutionScenarioSpec`, `AttackCandidate`, and
`ExecutionBudget` without defining Benchmark entities.
