"""Throwaway validation of Inspect AI's per-sample execution lifecycle."""

from __future__ import annotations

import json
import tempfile
from importlib.metadata import version

from inspect_ai import Task, eval
from inspect_ai.dataset import Sample
from inspect_ai.model import ModelOutput, get_model
from inspect_ai.scorer import CORRECT, INCORRECT, Score, Scorer, Target, scorer
from inspect_ai.solver import Generate, Solver, TaskState, solver
from inspect_ai.tool import Tool, tool
from inspect_ai.util import sandbox

RUN_ID = "inspect-spike-run-001"
MARKER_PATH = "marker.txt"
MARKER_CONTENT = "controlled-side-effect"


@tool
def write_marker() -> Tool:
    async def execute(path: str, contents: str) -> str:
        """Write a marker into the current sample sandbox.

        Args:
            path: Relative marker path in the sample sandbox.
            contents: Exact marker contents to write.

        Returns:
            A stable acknowledgement string.
        """
        await sandbox().write_file(path, contents)
        return "marker-written"

    return execute


@scorer(metrics=[])
def marker_assertion() -> Scorer:
    async def score(state: TaskState, target: Target) -> Score:
        del state, target
        contents = await sandbox().read_file(MARKER_PATH)
        return Score(
            value=CORRECT if contents == MARKER_CONTENT else INCORRECT,
            answer=contents,
            explanation="Marker observed from the scorer in the active sample sandbox.",
        )

    return score


@solver
def marker_solver() -> Solver:
    async def solve(state: TaskState, generate: Generate) -> TaskState:
        state.tools = [write_marker()]
        state.metadata["custom_solver"] = "marker_solver"
        return await generate(state)

    return solve


def main() -> None:
    task = Task(
        name="inspect_execution_model_spike",
        dataset=[
            Sample(
                id=RUN_ID,
                input="Write the requested marker.",
                target=MARKER_CONTENT,
                metadata={"project_run_id": RUN_ID},
            )
        ],
        solver=marker_solver(),
        scorer=marker_assertion(),
        sandbox="local",
    )
    model = get_model(
        "mockllm/model",
        custom_outputs=[
            ModelOutput.for_tool_call(
                model="mockllm/model",
                tool_name="write_marker",
                tool_arguments={"path": MARKER_PATH, "contents": MARKER_CONTENT},
            ),
            ModelOutput.from_content(model="mockllm/model", content="Marker written."),
        ],
    )

    with tempfile.TemporaryDirectory(prefix="agentsec-inspect-log-") as log_dir:
        log = eval(
            task,
            model=model,
            log_dir=log_dir,
            display="none",
            message_limit=4,
        )[0]

        assert log.status == "success", log.error
        assert log.samples is not None and len(log.samples) == 1
        sample = log.samples[0]
        assert sample.id == RUN_ID
        assert sample.metadata["project_run_id"] == RUN_ID
        assert sample.metadata["custom_solver"] == "marker_solver"
        assert any(message.role == "tool" for message in sample.messages)
        assert sample.scores is not None
        score = next(iter(sample.scores.values()))
        assert score.value == CORRECT

        print(
            json.dumps(
                {
                    "inspect_ai": version("inspect-ai"),
                    "log_status": log.status,
                    "sample_id": sample.id,
                    "project_run_id": sample.metadata["project_run_id"],
                    "custom_solver": sample.metadata["custom_solver"],
                    "score": score.value,
                    "tool_messages": sum(message.role == "tool" for message in sample.messages),
                },
                sort_keys=True,
            )
        )


if __name__ == "__main__":
    main()
