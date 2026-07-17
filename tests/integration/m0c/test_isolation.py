from __future__ import annotations

import asyncio
import inspect

import pytest
from pyrit.executor.attack.multi_turn.red_teaming import RedTeamingAttack
from pyrit.memory import CentralMemory

from agentsec_eval.assertions import ProgressState
from agentsec_eval.domain import CanonicalTraceEvent
from agentsec_eval.integrations.pyrit import AttackPolicyResult, AttackPolicyStopReason
from agentsec_eval.integrations.pyrit import policy as policy_module

from .conftest import (
    AdversarialTargetFactory,
    RecordingTargetSession,
    SequenceOracle,
    make_decision,
)
from .test_policy import run_owned_policy

pytestmark = [
    pytest.mark.integration,
    pytest.mark.pyrit,
    pytest.mark.filterwarnings(
        "ignore:.*labels=.*deprecated and will be removed in 0.16.0.*:DeprecationWarning"
    ),
]

PolicyRun = tuple[
    AttackPolicyResult,
    RecordingTargetSession,
    SequenceOracle,
    AdversarialTargetFactory,
    list[CanonicalTraceEvent],
]


def test_policy_uses_pinned_red_teaming_extension_without_attack_executor() -> None:
    controlled_attack = policy_module._ProjectControlledRedTeamingAttack

    assert issubclass(controlled_attack, RedTeamingAttack)
    assert "_perform_async" in controlled_attack.__dict__
    assert policy_module._POLICY_VERSION == "0.14.0"
    assert "AttackExecutor" not in inspect.getsource(policy_module)


def test_concurrent_callers_isolate_messages_scores_evidence_and_attack_results() -> None:
    previous_memory = CentralMemory._memory_instance

    async def run_both() -> tuple[PolicyRun, PolicyRun]:
        first_task = asyncio.create_task(
            run_owned_policy(
                run_id="run-1",
                decisions=[make_decision(ProgressState.OBJECTIVE_ACHIEVED, run_id="run-1")],
                max_turns=2,
            )
        )
        second_task = asyncio.create_task(
            run_owned_policy(
                run_id="run-2",
                decisions=[make_decision(ProgressState.TERMINAL_BLOCKED, run_id="run-2")],
                max_turns=2,
            )
        )
        return await asyncio.gather(first_task, second_task)

    first_run, second_run = asyncio.run(run_both())
    first, first_session, _, _, first_trace = first_run
    second, second_session, _, _, second_trace = second_run

    assert first.stop_reason is AttackPolicyStopReason.OBJECTIVE_ACHIEVED
    assert second.stop_reason is AttackPolicyStopReason.TERMINAL_BLOCKED
    assert first.raw_artifact["run_ids"] == ["run-1"]
    assert second.raw_artifact["run_ids"] == ["run-2"]
    assert first.raw_artifact["score_count"] == second.raw_artifact["score_count"] == 1
    assert first.raw_artifact["attack_result_count"] == 1
    assert second.raw_artifact["attack_result_count"] == 1

    first_messages = first.raw_artifact["messages"]
    second_messages = second.raw_artifact["messages"]
    assert isinstance(first_messages, list)
    assert isinstance(second_messages, list)
    assert "response-run-1-1" in str(first_messages)
    assert "response-run-2-1" not in str(first_messages)
    assert "response-run-2-1" in str(second_messages)
    assert "response-run-1-1" not in str(second_messages)

    first_conversations = first.raw_artifact["conversation_ids"]
    second_conversations = second.raw_artifact["conversation_ids"]
    assert isinstance(first_conversations, list)
    assert isinstance(second_conversations, list)
    assert first.objective_conversation_id in first_conversations
    assert first.adversarial_conversation_id in first_conversations
    assert second.objective_conversation_id in second_conversations
    assert second.adversarial_conversation_id in second_conversations
    assert set(first_conversations).isdisjoint(second_conversations)

    first_score_ids = first.raw_artifact["score_ids"]
    second_score_ids = second.raw_artifact["score_ids"]
    first_result_ids = first.raw_artifact["attack_result_ids"]
    second_result_ids = second.raw_artifact["attack_result_ids"]
    assert isinstance(first_score_ids, list)
    assert isinstance(second_score_ids, list)
    assert isinstance(first_result_ids, list)
    assert isinstance(second_result_ids, list)
    assert set(first_score_ids).isdisjoint(second_score_ids)
    assert set(first_result_ids).isdisjoint(second_result_ids)

    first_json = first.model_dump_json()
    second_json = second.model_dump_json()
    assert "evidence-run-1-1" in first_json
    assert "evidence-run-2-1" not in first_json
    assert "evidence-run-2-1" in second_json
    assert "evidence-run-1-1" not in second_json
    assert all(event.run_id == "run-1" for event in first_trace)
    assert all(event.run_id == "run-2" for event in second_trace)
    assert first_session.closed is second_session.closed is True
    assert CentralMemory._memory_instance is previous_memory
