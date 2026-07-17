"""Serialized, resettable PyRIT memory lifecycle for one project Run."""

from __future__ import annotations

import asyncio
import threading
from types import TracebackType
from typing import Final, cast

from pydantic import JsonValue
from pyrit.memory import CentralMemory, MemoryInterface, SQLiteMemory
from pyrit.models import AttackResult

_RUN_LABEL: Final = "agentsec_eval.run_id"


class _AgentSecEvalSQLiteMemory(SQLiteMemory):
    """Integration-owned singleton, distinct from a caller's SQLiteMemory."""


class PyRITMemoryScope:
    """Exclusively bind, snapshot, and clear PyRIT memory for one Run."""

    _process_lock = threading.Lock()

    def __init__(self, *, run_id: str) -> None:
        normalized_run_id = run_id.strip()
        if not normalized_run_id:
            raise ValueError("run_id must not be blank")
        self._run_id = normalized_run_id
        self._previous_memory: MemoryInterface | None = None
        self._memory: MemoryInterface | None = None
        self._artifact: dict[str, JsonValue] | None = None
        self._attack_results: tuple[AttackResult, ...] = ()
        self._cleanup_error: Exception | None = None
        self._lock_acquired = False
        self._entered = False

    @property
    def run_id(self) -> str:
        return self._run_id

    @property
    def labels(self) -> dict[str, str]:
        return {_RUN_LABEL: self._run_id}

    @property
    def memory(self) -> MemoryInterface:
        if self._memory is None or not self._entered:
            raise RuntimeError("PyRITMemoryScope is not active")
        return self._memory

    @property
    def artifact(self) -> dict[str, JsonValue]:
        if self._artifact is None:
            raise RuntimeError("PyRIT memory artifact is not available before scope exit")
        return self._artifact

    @property
    def raw_artifact_ref(self) -> str:
        return f"agentsec-eval:{self._run_id}:pyrit-memory"

    @property
    def attack_results(self) -> tuple[AttackResult, ...]:
        if self._entered:
            return tuple(self.memory.get_attack_results())
        return self._attack_results

    @property
    def cleanup_error(self) -> Exception | None:
        return self._cleanup_error

    async def __aenter__(self) -> PyRITMemoryScope:
        if self._entered or self._lock_acquired:
            raise RuntimeError("PyRITMemoryScope cannot be entered more than once")
        await self._acquire_process_lock()
        self._lock_acquired = True
        try:
            self._previous_memory = CentralMemory._memory_instance
            memory = cast(
                MemoryInterface,
                _AgentSecEvalSQLiteMemory(db_path=":memory:", silent=True),
            )
            memory.reset_database()
            self._memory = memory
            CentralMemory.set_memory_instance(memory)
            self._entered = True
            return self
        except BaseException:
            CentralMemory._memory_instance = self._previous_memory
            self._release_process_lock()
            raise

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        del exc_type, traceback
        cleanup_error: Exception | None = None
        try:
            self._capture_artifact()
        except Exception as error:
            cleanup_error = error
        try:
            if self._memory is not None:
                self._memory.reset_database()
        except Exception as error:
            cleanup_error = cleanup_error or error
        finally:
            self._entered = False
            CentralMemory._memory_instance = self._previous_memory
            self._release_process_lock()
        self._cleanup_error = cleanup_error
        if cleanup_error is not None and exc is None:
            raise cleanup_error
        return False

    async def _acquire_process_lock(self) -> None:
        acquire_task = asyncio.create_task(asyncio.to_thread(self._process_lock.acquire))
        try:
            acquired = await asyncio.shield(acquire_task)
        except BaseException:
            acquired = await acquire_task
            if acquired:
                self._process_lock.release()
            raise
        if not acquired:
            raise RuntimeError("failed to acquire the PyRIT memory process lock")

    def _release_process_lock(self) -> None:
        if self._lock_acquired:
            self._process_lock.release()
            self._lock_acquired = False

    def _capture_artifact(self) -> None:
        if self._memory is None:
            return
        messages = list(self._memory.get_message_pieces())
        attack_results = tuple(self._memory.get_attack_results())
        scores_by_id = {str(score.id): score for piece in messages for score in piece.scores}
        run_ids = {
            label
            for label in [
                *(piece.labels.get(_RUN_LABEL) for piece in messages),
                *(result.labels.get(_RUN_LABEL) for result in attack_results),
            ]
            if label is not None
        }
        conversation_ids = {
            *(piece.conversation_id for piece in messages),
            *(result.conversation_id for result in attack_results),
        }
        run_id_values = [cast(JsonValue, value) for value in sorted(run_ids)]
        conversation_id_values = [cast(JsonValue, value) for value in sorted(conversation_ids)]
        score_id_values = [cast(JsonValue, value) for value in sorted(scores_by_id)]
        attack_result_id_values = [
            cast(JsonValue, value)
            for value in sorted(result.attack_result_id for result in attack_results)
        ]
        message_values = [cast(JsonValue, piece.model_dump(mode="json")) for piece in messages]
        attack_result_values = [
            cast(JsonValue, result.model_dump(mode="json")) for result in attack_results
        ]
        self._attack_results = attack_results
        self._artifact = {
            "schema_version": 1,
            "run_ids": run_id_values,
            "conversation_ids": conversation_id_values,
            "message_count": len(messages),
            "score_count": len(scores_by_id),
            "attack_result_count": len(attack_results),
            "score_ids": score_id_values,
            "attack_result_ids": attack_result_id_values,
            "messages": message_values,
            "attack_results": attack_result_values,
        }
        invalid_message_labels = [
            piece.labels.get(_RUN_LABEL)
            for piece in messages
            if piece.labels.get(_RUN_LABEL) != self._run_id
        ]
        invalid_result_labels = [
            result.labels.get(_RUN_LABEL)
            for result in attack_results
            if result.labels.get(_RUN_LABEL) != self._run_id
        ]
        invalid_score_labels = [
            score.score_metadata.get("run_id") if score.score_metadata else None
            for score in scores_by_id.values()
            if not score.score_metadata or score.score_metadata.get("run_id") != self._run_id
        ]
        if invalid_message_labels or invalid_result_labels or invalid_score_labels:
            raise RuntimeError("PyRIT memory contains foreign or missing Run labels")
