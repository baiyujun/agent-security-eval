# Development Roadmap

The milestones are ordered to validate execution and assertion boundaries before adding adaptive
fuzzing complexity.

## M0: Validation phase complete

**Status: completed.** M0-A, M0-B, and M0-C are merged and validated. Together they establish the
bounded Inspect execution, assertion-backed progress, and adaptive per-Run PyRIT policy boundaries.
They do not constitute a complete security evaluation product. See the
[M0 closeout report](m0-closeout.md).

## M0-A: Inspect AI execution model validation

**Status: merged and validated in PR #4 (`69328a6`) on 2026-07-17.**

One project-owned run description now executes as one isolated Inspect Sample and returns correlated
project-native observations without making Inspect AI the domain model. Automated tests cover two
concurrent Docker Compose Samples, one three-turn Target Session per Sample, Store/Canary/effect
isolation, direct environment confirmation, structured Harness scoring, and injected-failure Docker
cleanup. See [the M0-A validation report](m0-a-inspect-validation.md).

This is a bounded execution-model validation, not the production backend or a complete assertion
engine. The earlier `experiments/inspect-execution-model/` code remains a throwaway research spike.

## M0-B: Assertion-backed PyRIT scorer validation

**Status: merged and validated in PR #7 (`d0272e8`) on 2026-07-17.**

A project-owned Progress Oracle now maps four runtime states into a pinned PyRIT `0.14.0`
`TrueFalseScorer` while preserving the complete decision as versioned metadata. Only objective
achievement maps to true; blocked and invalid Runs remain false but terminal and distinguishable.
The public blocked/error scorer path retains the Oracle decision, and internal audit rationale is
separate from attacker-safe policy feedback. The optional integration does not implement an Attack
Strategy, policy stopping, PromptTarget, or Final Assertion Engine. See
[the M0-B validation report](m0-b-pyrit-scorer-validation.md).

## M0-C: PyRIT Attack Policy embedding validation

**Status: merged and validated in PR #8 (`e954677`) on 2026-07-17.**

One project-owned policy now uses the pinned PyRIT `0.14.0` red-teaming lifecycle inside a single
Run while retaining project control of terminal states and turn budget. It adapts one already-open
Target Session, stops immediately for objective achievement, terminal block, and invalid Runs,
records trusted per-turn decisions, and keeps final security truth out of `AttackPolicyResult`.
Concurrent callers are accepted through a serialized in-process PyRIT Memory Scope; this is a
safety boundary, not a claim of parallel policy execution. See [the M0-C validation
report](m0-c-pyrit-policy-validation.md).

## M1: Batch Security Eval

Execute reproducible batches against versioned targets and produce assertion-backed artifacts with
separately reported security and utility results.

## M2: Coverage-aware Corpus

Track scenario provenance, observed behavioral coverage, and reproducible vulnerability seeds.

## M3: Feedback-guided Fuzzing

Use bounded observation and assertion feedback to prioritize and mutate attacks across campaigns.

## M4: Adaptive Agent Fuzzing

Evaluate more capable adaptive attack policies after execution isolation, evidence integrity, and
regression guarantees are established.
