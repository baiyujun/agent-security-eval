# Architecture Baseline

## Purpose

The project evaluates tool-using Agents by actively executing attacks and checking observable
security effects. Its top-level control flow is:

```text
Campaign Controller
  -> Inspect AI execution backend
  -> Target Adapter / Target Session
  -> Observation Gateway
  -> Progress Oracle / Final Assertion Engine
  -> RunOutcome
  -> Feedback and Corpus Manager
  -> Artifact and Regression Store
```

## Control boundaries

The Campaign Controller is the only top-level controller. It selects corpus entries and attack
policies, creates execution specifications, dispatches work, and records feedback without
delegating campaign ownership to an integration framework.

Each `ExecutionRunSpec` maps to one independent execution-backend Sample. The Sample owns one
isolated run against one target configuration; multi-turn attack behavior occurs inside that run,
not by sharing mutable state between Samples.

Target Adapters translate project-native run instructions into a target framework and normalize
target responses, tool calls, guardrail events, and environment observations back into native
project types. External framework objects must not become the persistent domain contract.

The Progress Oracle may provide bounded feedback while a run is active. Only the project's Final
Assertion Engine may produce the formal final security decision. Assertions should prefer
deterministic tool, argument, ordering, guardrail, and environmental-effect evidence. Attack
generators and LLM graders are not authoritative sources of final truth.

`RunOutcome` keeps security findings, normal-task utility, evidence provenance, harness integrity,
and unresolved observations distinct. It is then available to feedback, corpus evolution,
reproduction, and regression workflows.

## Baseline status

This file is an architecture baseline for the clean repository. It does not claim that Inspect AI,
promptfoo, PyRIT, Target Adapters, observation capture, assertions, or storage integrations are
implemented.
