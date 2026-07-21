# M0 Validation Closeout

## Status

**COMPLETE.** The M0 execution, progress-oracle, and adaptive-attack-policy validation phase is
merged and validated. This is a bounded engineering baseline, not a production security evaluation
product.

## Goal

M0 tested whether the project can retain ownership of security-relevant contracts while reusing
pinned external frameworks at narrow boundaries:

1. execute one project Run through Inspect AI without making Inspect the domain model;
2. preserve a project-owned Progress Oracle through PyRIT's scorer interface; and
3. embed one adaptive PyRIT policy inside a Run without giving PyRIT Campaign or final-truth
   ownership.

## Delivery Evidence

| Milestone | Pull request | Reviewed Head | Squash merge | Result |
| --- | --- | --- | --- | --- |
| M0-A Inspect execution boundary | #4 | `9ea19b36ffe1fea947f98a55c153bc061638529a` | `69328a6a7e7d752d78fb16701db8339f1cfa1684` | PASS |
| M0-B assertion-backed progress scorer | #7 | `c23d208e1f618387010da97347950ba04f50509f` | `d0272e8140926cc1cf3a4510b598b323de4f850a` | PASS |
| M0-C per-Run adaptive PyRIT policy | #8 | `d9b1d5ae771dd9b9431f61bbb56b4cb1aa52eb0c` | `e954677b53a51a2ce7505b0730bae77daebc5686` | PASS |

The M0 implementation baseline is
`e954677b53a51a2ce7505b0730bae77daebc5686`. Architecture closeout subsequently merged in PR #11 at
`436551329aaaa8dfc6521bebc6e60d5731b35b89` without changing runtime code.

## Fixed Dependencies

| Dependency | Version | M0 role |
| --- | --- | --- |
| Python | `>=3.11` | Supported runtime and CI baseline |
| Inspect AI | `0.3.246` | Batch/Sample execution, Solver/Scorer lifecycle, Sandbox access, and EvalLog evidence |
| Pydantic | `>=2,<3` | Immutable project contracts and boundary validation |
| PyRIT | optional `0.14.0` | Progress scorer interface and adaptive multi-turn policy inside one Run |

Version changes require contract retesting. No third-party source or dataset is copied into the M0
runtime implementation.

## Validated Chain

```text
ExecutionRunSpec
  -> Inspect Sample and isolated Docker execution
  -> project TargetSession and CanonicalTraceEvent evidence
  -> project ProgressOracle / ProgressDecision
  -> AssertionBackedPyRITScorer
  -> project-controlled per-Run PyRIT policy and stopping
  -> AttackPolicyResult plus trusted trace and memory artifact
```

Inspect owns the execution mechanics inside its integration boundary. PyRIT owns adaptive turn
generation and scorer-compatible progress feedback inside one Run. The project owns all durable Run,
Target, trace, progress, stopping, and evidence contracts. `AttackPolicyResult` is not a final
security verdict.

## Verification Baseline

The final M0/architecture Head was revalidated on CPython 3.11.15 with Inspect AI `0.3.246` and
PyRIT `0.14.0`:

| Gate | Result |
| --- | --- |
| Ruff check and format check | PASS; 43 files formatted |
| Global MyPy | PASS; 26 source files |
| Core non-Docker Pytest | PASS; 54 passed, 2 deselected in the CI quality scope |
| M0-A Docker integration | PASS; 2 tests |
| M0-B scoped MyPy and Pytest | PASS; 4 typed files, 15 tests |
| M0-C scoped MyPy and Pytest | PASS; 14 typed files, 48 tests |
| GitHub Actions | PASS; `quality`, `m0a-docker`, `m0b-pyrit`, and `m0c-pyrit` |

The individual validation reports retain milestone-specific test matrices and reproduction details:

- [M0-A Inspect execution validation](m0-a-inspect-validation.md)
- [M0-B PyRIT scorer validation](m0-b-pyrit-scorer-validation.md)
- [M0-C PyRIT policy validation](m0-c-pyrit-policy-validation.md)

## Known Limitations

- M0-A is a validation Harness using a deterministic Fake Target and Inspect mock model, not a
  production execution backend.
- The project has no production Final Assertion Engine. M0-B validates progress decisions, not final
  vulnerability truth.
- PyRIT policy execution is serialized in-process around process-global `CentralMemory`; it is not a
  parallel policy backend.
- The pinned integration reads private `PromptTarget._memory` for compatibility enforcement. Issue
  [#9](https://github.com/baiyujun/agent-security-eval/issues/9) tracks this non-blocking debt.
- Cancellation, retry, resume, host termination, persistence, distributed scheduling, and broad
  multi-Target calibration are not validated as production behavior.
- No `BaseScenario`, `ScenarioCase`, Scenario Registry, Offline Benchmark Importer, dataset, Campaign
  Controller, corpus, or production artifact store is implemented by M0.

## M1 Boundary

The following work belongs to M1 or later and is not an M0 gap:

1. freeze `ScenarioCase -> CompiledRunInput / ExecutionRunSpec`;
2. define native scenario assets without duplicating M0 execution types;
3. validate the two Offline Benchmark Importer Spikes and per-asset rights gates;
4. build reproducible batch execution and assertion-backed security/utility artifacts; and
5. decide process/worker isolation before true parallel PyRIT policy execution.

M1 must preserve the accepted Offline Import / Native Runtime architecture. External Benchmark
runtimes remain isolated replay evidence, never production Campaign backends or final security truth.
