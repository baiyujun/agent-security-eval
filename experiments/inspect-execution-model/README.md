# Inspect AI Execution Model Spike

Status: throwaway experiment; not a production API.

## Hypothesis

Inspect AI can carry one project-owned run identifier through a `Sample`, execute a custom `Solver`
and tool in the sample sandbox, expose the resulting environment state to a custom `Scorer`, and
retain the conversation and score in the same `EvalLog` sample.

The experiment is pinned to Inspect AI `0.3.246` (tag commit
`05322696a0f784ec399ef6abbafd3d2a250ea9cc`). It intentionally does not add Inspect AI to this
project's dependencies.

## Run

From the repository root:

```bash
python3 -m venv /tmp/agentsec-inspect-spike
/tmp/agentsec-inspect-spike/bin/pip install "inspect-ai==0.3.246"
/tmp/agentsec-inspect-spike/bin/python experiments/inspect-execution-model/spike.py
```

The command exits non-zero if the custom Solver marker, run identifier, tool event, sandbox-backed
score, or sample log cannot be correlated. On success it prints a compact JSON summary.

Recorded on 2026-07-16 with the pinned version:

```json
{"custom_solver":"marker_solver","inspect_ai":"0.3.246","log_status":"success","project_run_id":"inspect-spike-run-001","sample_id":"inspect-spike-run-001","score":"C","tool_messages":1}
```

## Scope And Limitations

- `sandbox="local"` validates lifecycle and filesystem scoping, not security isolation. A Docker
  sandbox remains an implementation milestone.
- `mockllm/model` makes the run deterministic and requires no model credentials.
- `marker_solver` is a minimal custom `@solver`; it registers the tool and delegates the model/tool
  loop to Inspect's supplied `Generate` callback.
- The scorer demonstrates an extension boundary. Its score is not a project security verdict.
- The run identifier is metadata, not a proposed persistent domain schema.
- `EvalLog.samples` may be lazy. Consumers must materialize required fields while the backing log
  remains available; this spike reads them before its temporary log directory is removed.
- The experiment does not cover Campaign scheduling, external Agents, PyRIT, or promptfoo.

Delete this directory once equivalent tests exist around an accepted execution integration. Promote
any part only after the Inspect dependency version and the project's minimal cross-backend contract
have been approved.
