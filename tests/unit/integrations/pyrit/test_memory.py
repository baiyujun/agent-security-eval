from __future__ import annotations

import asyncio
from collections.abc import Iterator

import pytest
from pyrit.memory import CentralMemory, SQLiteMemory
from pyrit.models import AttackOutcome, AttackResult, MessagePiece, Score

from agentsec_eval.integrations.pyrit import PyRITMemoryScope

pytestmark = pytest.mark.pyrit


class _PreviousTestMemory(SQLiteMemory):
    pass


@pytest.fixture
def previous_memory() -> Iterator[SQLiteMemory]:
    original = CentralMemory._memory_instance
    memory = _PreviousTestMemory(db_path=":memory:", silent=True)
    memory.reset_database()
    CentralMemory.set_memory_instance(memory)
    try:
        yield memory
    finally:
        memory.reset_database()
        CentralMemory._memory_instance = original


def add_run_artifacts(scope: PyRITMemoryScope, *, value: str) -> None:
    piece = MessagePiece(
        role="assistant",
        original_value=value,
        conversation_id=f"conversation-{scope.run_id}",
    )
    piece.labels = scope.labels
    scope.memory.add_message_to_memory(request=piece.to_message())
    score = Score(
        score_value="false",
        score_type="true_false",
        score_category=["agent_security_eval"],
        score_rationale="sanitized feedback",
        score_metadata={"run_id": scope.run_id},
        message_piece_id=piece.id,
    )
    scope.memory.add_scores_to_memory(scores=[score])
    scope.memory.add_attack_results_to_memory(
        attack_results=[
            AttackResult(
                conversation_id=f"conversation-{scope.run_id}",
                objective=f"objective-{scope.run_id}",
                outcome=AttackOutcome.FAILURE,
                labels=scope.labels,
            )
        ]
    )


def test_memory_scope_labels_snapshots_cleans_and_restores_previous_memory(
    previous_memory: SQLiteMemory,
) -> None:
    scope = PyRITMemoryScope(run_id="run-1")

    async def exercise() -> None:
        async with scope:
            assert CentralMemory.get_memory_instance() is scope.memory
            assert scope.labels == {"agentsec_eval.run_id": "run-1"}
            add_run_artifacts(scope, value="run-1-response")
            assert len(scope.attack_results) == 1

    asyncio.run(exercise())

    assert CentralMemory.get_memory_instance() is previous_memory
    assert scope.artifact["schema_version"] == 1
    assert scope.artifact["run_ids"] == ["run-1"]
    assert scope.artifact["conversation_ids"] == ["conversation-run-1"]
    assert scope.artifact["message_count"] == 1
    assert scope.artifact["score_count"] == 1
    assert scope.artifact["attack_result_count"] == 1
    score_ids = scope.artifact["score_ids"]
    attack_result_ids = scope.artifact["attack_result_ids"]
    assert isinstance(score_ids, list)
    assert isinstance(attack_result_ids, list)
    assert len(score_ids) == 1
    assert len(attack_result_ids) == 1
    messages = scope.artifact["messages"]
    attack_results = scope.artifact["attack_results"]
    assert isinstance(messages, list)
    assert isinstance(attack_results, list)
    assert isinstance(messages[0], dict)
    assert isinstance(attack_results[0], dict)
    message = messages[0]
    scores = message["scores"]
    assert isinstance(scores, list)
    assert isinstance(scores[0], dict)
    assert message["converted_value"] == "run-1-response"
    assert message["labels"] == {"agentsec_eval.run_id": "run-1"}
    assert scores[0]["score_metadata"] == {"run_id": "run-1"}
    assert attack_results[0]["labels"] == {"agentsec_eval.run_id": "run-1"}

    async def verify_empty_next_scope() -> None:
        async with PyRITMemoryScope(run_id="run-2") as second:
            assert second.memory.get_message_pieces() == []
            assert second.memory.get_attack_results() == []

    asyncio.run(verify_empty_next_scope())
    assert CentralMemory.get_memory_instance() is previous_memory


def test_memory_scope_serializes_concurrent_callers_without_cross_run_data(
    previous_memory: SQLiteMemory,
) -> None:
    active_runs: set[str] = set()
    max_active = 0

    async def run_scope(run_id: str) -> dict[str, object]:
        nonlocal max_active
        scope = PyRITMemoryScope(run_id=run_id)
        async with scope:
            active_runs.add(run_id)
            max_active = max(max_active, len(active_runs))
            add_run_artifacts(scope, value=f"{run_id}-response")
            await asyncio.sleep(0.02)
            active_runs.remove(run_id)
        return dict(scope.artifact)

    async def run_both() -> tuple[dict[str, object], dict[str, object]]:
        first_task = asyncio.create_task(run_scope("run-1"))
        second_task = asyncio.create_task(run_scope("run-2"))
        first, second = await asyncio.gather(first_task, second_task)
        return first, second

    first, second = asyncio.run(run_both())

    assert max_active == 1
    assert first["run_ids"] == ["run-1"]
    assert second["run_ids"] == ["run-2"]
    assert first["conversation_ids"] == ["conversation-run-1"]
    assert second["conversation_ids"] == ["conversation-run-2"]
    assert CentralMemory.get_memory_instance() is previous_memory


def test_memory_scope_restores_and_releases_after_primary_error(
    previous_memory: SQLiteMemory,
) -> None:
    class InjectedError(RuntimeError):
        pass

    failed_scope = PyRITMemoryScope(run_id="run-failed")

    async def fail_inside_scope() -> None:
        async with failed_scope:
            add_run_artifacts(failed_scope, value="failed-response")
            raise InjectedError("injected policy failure")

    with pytest.raises(InjectedError, match="injected policy failure"):
        asyncio.run(fail_inside_scope())

    assert failed_scope.artifact["run_ids"] == ["run-failed"]
    assert CentralMemory.get_memory_instance() is previous_memory

    async def enter_after_failure() -> None:
        async with PyRITMemoryScope(run_id="run-after-failure") as scope:
            assert scope.memory.get_message_pieces() == []

    asyncio.run(enter_after_failure())


def test_memory_scope_restores_and_releases_after_cancellation(
    previous_memory: SQLiteMemory,
) -> None:
    cancelled_scope = PyRITMemoryScope(run_id="run-cancelled")

    async def cancel_inside_scope() -> None:
        entered = asyncio.Event()
        never = asyncio.Event()

        async def hold_scope() -> None:
            async with cancelled_scope:
                add_run_artifacts(cancelled_scope, value="cancelled-response")
                entered.set()
                await never.wait()

        task = asyncio.create_task(hold_scope())
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(cancel_inside_scope())

    assert cancelled_scope.artifact["run_ids"] == ["run-cancelled"]
    assert CentralMemory.get_memory_instance() is previous_memory

    async def enter_after_cancellation() -> None:
        async with PyRITMemoryScope(run_id="run-after-cancel"):
            return None

    asyncio.run(enter_after_cancellation())


def test_memory_scope_rejects_unlabeled_or_foreign_data_and_still_cleans(
    previous_memory: SQLiteMemory,
) -> None:
    scope = PyRITMemoryScope(run_id="run-1")

    async def add_foreign_message() -> None:
        async with scope:
            piece = MessagePiece(
                role="assistant",
                original_value="foreign",
                conversation_id="conversation-run-2",
            )
            piece.labels = {"agentsec_eval.run_id": "run-2"}
            scope.memory.add_message_to_memory(request=piece.to_message())

    with pytest.raises(RuntimeError, match="foreign or missing Run labels"):
        asyncio.run(add_foreign_message())

    assert CentralMemory.get_memory_instance() is previous_memory


@pytest.mark.parametrize(
    "score_metadata",
    [None, {}, {"run_id": "run-2"}],
    ids=["missing-metadata", "missing-run-id", "foreign-run-id"],
)
def test_memory_scope_rejects_scores_without_current_run_id(
    previous_memory: SQLiteMemory,
    score_metadata: dict[str, str | int | float] | None,
) -> None:
    scope = PyRITMemoryScope(run_id="run-1")

    async def add_invalid_score() -> None:
        async with scope:
            piece = MessagePiece(
                role="assistant",
                original_value="untrusted score",
                conversation_id="conversation-run-1",
            )
            piece.labels = scope.labels
            scope.memory.add_message_to_memory(request=piece.to_message())
            scope.memory.add_scores_to_memory(
                scores=[
                    Score(
                        score_value="false",
                        score_type="true_false",
                        score_category=["agent_security_eval"],
                        score_rationale="sanitized feedback",
                        score_metadata=score_metadata,
                        message_piece_id=piece.id,
                    )
                ]
            )

    with pytest.raises(RuntimeError, match="foreign or missing Run labels"):
        asyncio.run(add_invalid_score())

    assert CentralMemory.get_memory_instance() is previous_memory
