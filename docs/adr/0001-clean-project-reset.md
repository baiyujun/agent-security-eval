# ADR-0001: Start the Agent Security Evaluation System in a Clean Repository

- Status: Accepted
- Date: 2026-07-15

## Context

The legacy `intent-engine` repository implements a layered intent-recognition and online guardrail
prototype. Its principal abstractions are text-oriented classification tiers and an online
decision Pipeline.

The new system actively attacks tool-using Agents, executes scenarios in isolated environments,
captures real trajectories and environmental evidence, evaluates deterministic assertions, and
preserves vulnerabilities for reproduction and regression.

These systems do not have sufficient domain continuity for a direct incremental refactor. Reusing
the old repository would preserve misleading module boundaries, data assumptions, and history in
the new project's foundation.

## Decision

Preserve the complete `intent-engine` repository and Git history as a legacy archive. Build the
Agent security evaluation and fuzzing system in an independent repository with a clean Git history,
new package namespace, and architecture documentation.

No legacy Tier 0-3 implementation, text-classification dataset, model artifact, or Pipeline is
copied into the new repository.

## Consequences

- Historical experiments remain auditable and reproducible in the archived repository.
- The new system can define execution, observation, assertion, outcome, corpus, and regression
  boundaries without compatibility obligations to the old prototype.
- Useful historical ideas must be re-evaluated and recorded as explicit references rather than
  inherited silently.
- Migration requires links between the repositories and separate maintenance of provenance.

## Rejected alternatives

### Refactor the old `master` directly

Rejected because it would mix two incompatible product histories and make obsolete abstractions
appear foundational to the new system.

### Reuse the repository with an orphan branch

Rejected because the repository identity, issues, release history, and default navigation would
still conflate the projects even if the branch history were disconnected.

### Copy the complete old codebase into a new repository

Rejected because it would carry obsolete business code, model artifacts, datasets, and dependency
assumptions into the clean project without a justified interface.
