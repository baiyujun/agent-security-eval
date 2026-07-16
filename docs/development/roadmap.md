# Development Roadmap

The milestones are ordered to validate execution and assertion boundaries before adding adaptive
fuzzing complexity.

## M0-A: Inspect AI execution model validation

**Status: validated locally on 2026-07-16; Draft PR CI is the delivery gate.**

One project-owned run description now executes as one isolated Inspect Sample and returns correlated
project-native observations without making Inspect AI the domain model. Automated tests cover two
concurrent Docker Compose Samples, one three-turn Target Session per Sample, Store/Canary/effect
isolation, direct environment confirmation, structured Harness scoring, and injected-failure Docker
cleanup. See [the M0-A validation report](m0-a-inspect-validation.md).

This is a bounded execution-model validation, not the production backend or a complete assertion
engine. The earlier `experiments/inspect-execution-model/` code remains a throwaway research spike.

## M0-B: Assertion-backed PyRIT scorer validation

**Status: not started.**

Validate that a PyRIT-compatible scorer can consume a project assertion result while the Final
Assertion Engine remains the source of truth.

## M0-C: PyRIT Attack Policy embedding validation

**Status: not started.**

Validate PyRIT as an adaptive policy inside one Run without giving it campaign-level control.

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
