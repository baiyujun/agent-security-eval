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

Inspect AI is the planned Batch/Sample execution runtime. The candidate mapping is one independent
run against one target configuration per Sample; the current spike proves one Sample's lifecycle,
not concurrent isolation or retry behavior. Multi-turn PyRIT behavior, if enabled, remains inside a
run and does not acquire cross-run scheduling authority.

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

## Accepted reference reuse boundary

[ADR-0002](../adr/0002-offline-import-native-runtime.md) accepts external benchmarks as source
languages for offline import into project-native Scenario Packs. The project runtime remains the
sole production runtime; long-lived upstream runtime adapters are prohibited. The fixed commits,
source paths, reuse modes, and license gates supporting that decision are recorded in the
[reference environment source audit](reference-reuse-audit.md).

## Candidate Designs

The source audit and architecture comparison are documented in
[Reference Reuse Analysis](../reference-reuse-analysis.md) and
[Reference-Informed Architecture Options](reference-informed-options.md). Those documents recommend
a direction for the next experiment; they do not claim that Inspect AI, promptfoo, PyRIT,
observation capture, assertions, or storage integrations are implemented.
