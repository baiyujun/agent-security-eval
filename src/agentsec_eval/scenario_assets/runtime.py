"""Contract-test harness for compiled scenario inputs.

This module is intentionally outside the production execution path. Production execution maps
``ExecutionRunSpec`` to one Inspect ``Sample`` through ``agentsec_eval.execution``. The harness
below only lets tests exercise Target and environment protocols; it does not adjudicate evidence
or produce a formal project result.
"""

from __future__ import annotations

from typing import Protocol

from agentsec_eval.scenario_assets.compiler import CompiledRunInput, compiled_input_digest
from agentsec_eval.scenario_assets.enums import ProbeOracleCategory
from agentsec_eval.scenario_assets.models import (
    AssetId,
    FrozenModel,
    NativeScenarioPack,
    ProbeDefinition,
    ResetStep,
    Sha256Digest,
    StrictText,
)
from agentsec_eval.scenario_assets.validation import validate_pack
from agentsec_eval.targets.protocol import TargetAdapter, TargetTurnResult

CONTRACT_TEST_ONLY = True


class ScenarioEnvironment(Protocol):
    async def observe(
        self,
        probe: ProbeDefinition,
        *,
        compiled: CompiledRunInput,
        turn_result: TargetTurnResult,
    ) -> str: ...

    async def apply_reset(self, step: ResetStep) -> None: ...

    async def state_digest(self) -> str: ...


class ContractProbeObservation(FrozenModel):
    probe_id: AssetId
    category: ProbeOracleCategory
    value: StrictText


class ContractHarnessRecord(FrozenModel):
    """Raw contract-test observations with no formal adjudication semantics."""

    run_id: AssetId
    pack_id: AssetId
    case_id: AssetId
    session_id: AssetId
    target_response: str
    observations: tuple[ContractProbeObservation, ...]
    reset_state_digest: Sha256Digest


async def exercise_compiled_case_contract(
    compiled: CompiledRunInput,
    pack: NativeScenarioPack,
    target_adapter: TargetAdapter,
    environment: ScenarioEnvironment,
) -> ContractHarnessRecord:
    """Exercise test doubles without claiming production execution or final truth."""

    validated_pack = validate_pack(pack)
    validated_compiled = CompiledRunInput.model_validate(compiled.model_dump(mode="python"))
    if validated_compiled.output_digest != compiled_input_digest(validated_compiled):
        raise ValueError("compiled input digest is invalid")
    if validated_compiled.pack_id != validated_pack.pack_id:
        raise ValueError("compiled input does not belong to the supplied pack")
    cases = {case.case_id: case for case in validated_pack.cases}
    case = cases.get(validated_compiled.case_id)
    if case is None or case.case_version != validated_compiled.case_version:
        raise ValueError("compiled case identity/version does not resolve in the supplied pack")

    session = await target_adapter.open_session(validated_compiled.execution_spec)
    try:
        turn_result = await session.send(validated_compiled.agent_visible_prompt)
    finally:
        await session.close()

    suite = next(
        suite for suite in validated_pack.oracle_suites if suite.suite_id == case.oracle_suite_id
    )
    observations: list[ContractProbeObservation] = []
    for bundle in suite.bundles:
        for probe in bundle.probes:
            observations.append(
                ContractProbeObservation(
                    probe_id=probe.probe_id,
                    category=bundle.category,
                    value=await environment.observe(
                        probe,
                        compiled=validated_compiled,
                        turn_result=turn_result,
                    ),
                )
            )

    reset = next(
        contract
        for contract in validated_pack.reset_contracts
        if contract.reset_contract_id == case.reset_contract_id
    )
    for step in reset.steps:
        await environment.apply_reset(step)
    reset_state_digest = await environment.state_digest()

    return ContractHarnessRecord(
        run_id=validated_compiled.execution_spec.run_id,
        pack_id=validated_pack.pack_id,
        case_id=case.case_id,
        session_id=session.session_id,
        target_response=turn_result.response,
        observations=tuple(observations),
        reset_state_digest=reset_state_digest,
    )


__all__ = [
    "CONTRACT_TEST_ONLY",
    "ContractHarnessRecord",
    "ContractProbeObservation",
    "ScenarioEnvironment",
    "exercise_compiled_case_contract",
]
