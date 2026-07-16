# Development Roadmap

The milestones are ordered to validate execution and assertion boundaries before adding adaptive
fuzzing complexity.

## M0-A: Inspect AI execution model validation

Validate that one project-owned run description can execute as one isolated Sample and return
correlated observations without making Inspect AI the project domain model. The current throwaway
spike verifies the basic lifecycle with a mock model and local sandbox; Docker isolation, a real
target, and a durable boundary remain unvalidated.

## M0-B: Assertion-backed PyRIT scorer validation

Validate that a PyRIT-compatible scorer can consume a project assertion result while the Final
Assertion Engine remains the source of truth.

## M0-C: PyRIT Attack Policy embedding validation

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
