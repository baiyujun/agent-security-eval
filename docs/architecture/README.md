# Architecture Constraints

## Purpose

The project evaluates tool-using Agents by actively executing attacks and checking observable
security effects. The constraints below are accepted; they do not select a final directory layout,
set of classes, or persistence schema.

```text
Campaign Controller
  -> Inspect AI Batch/Sample execution
       -> optional PyRIT multi-turn policy within one run
       -> complete Agent system configuration under test
  -> project-owned evidence and final assertion
  -> separately recorded security / attack progress / control / utility
  -> feedback, replay, and regression responsibilities
```

## Control boundaries

The Campaign Controller is the only top-level controller. It selects work across runs and records
feedback without delegating campaign ownership to an integration framework.

Inspect AI is the validated Batch/Sample execution runtime. M0-A proves that concurrently executed
Samples remain isolated for the validated success and injected-failure paths; it does not validate
retry, resume, cancellation, or host-termination behavior. Multi-turn PyRIT behavior, if enabled,
remains inside a run and does not acquire cross-run scheduling authority.

promptfoo may generate attack candidates, but it does not execute targets or adjudicate results in
the project workflow. All target calls must pass through a project-owned observation boundary so
that tool calls, guardrail events, and environmental effects have explicit provenance.

Attack-progress signals may provide bounded feedback while a run is active. Only the project's Final
Assertion Engine may produce the formal final security decision. Assertions should prefer
deterministic tool, argument, ordering, guardrail, and environmental-effect evidence. Attack
generators and LLM graders are not authoritative sources of final truth.

Security findings, attack progress, control results, normal-task utility, evidence provenance,
harness integrity, and unresolved observations must remain distinct. Third-party runtime objects may
be used inside an integration, but they are not automatically the project's durable contract.

## Architecture References

The source audit and architecture comparison are documented in
[Reference Reuse Analysis](../reference-reuse-analysis.md) and
[Reference-Informed Architecture Options](reference-informed-options.md). Those documents record
research boundaries and follow-up work; they do not claim that Inspect AI, promptfoo, PyRIT,
observation capture, assertions, or storage integrations are implemented.

## Scenario Asset Decisions

- [ADR-0002: Offline Import / Native Runtime](../adr/0002-offline-import-native-runtime.md)
  is the accepted external Benchmark reuse boundary.
- [Scenario and Data Assets v1.1](scenario-data-assets-v1.1.md) is the accepted, canonical
  scenario-assets plan on `main`.
- [Reference Reuse Audit](reference-reuse-audit.md) maps fixed source evidence to the selected
  reuse boundary without duplicating the source-lock manifests.
- [Importer Spike Plan](../development/importer-spike-plan.md) defines the two initial offline
  conversion proofs and their optional upstream replay comparison.
