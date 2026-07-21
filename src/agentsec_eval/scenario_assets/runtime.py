"""Project-owned execution of compiled native scenario cases."""

from __future__ import annotations

from typing import Protocol

from agentsec_eval.scenario_assets.compiler import (
    CompiledRunInput,
    compiled_input_digest,
)
from agentsec_eval.scenario_assets.enums import OracleExpectation, ProbeOracleCategory
from agentsec_eval.scenario_assets.models import (
    AssetId,
    FrozenModel,
    NativeScenarioPack,
    ProbeDefinition,
    ResetStep,
    StrictText,
)
from agentsec_eval.scenario_assets.validation import validate_pack
from agentsec_eval.targets.protocol import TargetAdapter, TargetTurnResult


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


class ProbeObservation(FrozenModel):
    probe_id: AssetId
    category: ProbeOracleCategory
    value: StrictText


class OracleResult(FrozenModel):
    oracle_id: AssetId
    category: ProbeOracleCategory
    passed: bool
    detail: StrictText


class ProbeOracleBundleResult(FrozenModel):
    category: ProbeOracleCategory
    observations: tuple[ProbeObservation, ...]
    oracle_results: tuple[OracleResult, ...]
    passed: bool


class NativeExecutionResult(FrozenModel):
    run_id: AssetId
    pack_id: AssetId
    case_id: AssetId
    session_id: AssetId
    target_response: str
    bundle_results: tuple[ProbeOracleBundleResult, ...]
    reset_baseline_digest: str
    passed: bool


def _runtime_observation(
    category: ProbeOracleCategory,
    *,
    compiled: CompiledRunInput,
    attack_present: bool,
    session_closed: bool,
    reset_digest: str,
) -> str:
    if category is ProbeOracleCategory.ATTACK_PROGRESS:
        return "attack_delivered" if attack_present else "no_attack_control"
    if category is ProbeOracleCategory.HARNESS_INTEGRITY:
        return "session_closed" if session_closed else "session_open"
    if category is ProbeOracleCategory.RESET:
        return reset_digest
    if category is ProbeOracleCategory.REPRODUCIBILITY:
        return compiled_input_digest(compiled)
    raise ValueError(f"category requires an environment observation: {category.value}")


def _evaluate(expectation: OracleExpectation, value: str, expected_value: str) -> bool:
    if expectation is OracleExpectation.PRESENT:
        return bool(value)
    if expectation is OracleExpectation.ABSENT:
        return not value
    if expectation is OracleExpectation.EQUALS:
        return value == expected_value
    if expectation is OracleExpectation.UNCHANGED:
        return value == expected_value
    if expectation is OracleExpectation.ORDERED:
        return value == expected_value
    return False


async def execute_compiled_case(
    compiled: CompiledRunInput,
    pack: NativeScenarioPack,
    target_adapter: TargetAdapter,
    environment: ScenarioEnvironment,
) -> NativeExecutionResult:
    """Execute and adjudicate one compiled case under project-owned lifecycle control."""

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
    if set(validated_compiled.source_provenance_ids) != {
        provenance.provenance_id for provenance in validated_pack.provenance
    }:
        raise ValueError("compiled provenance does not recover the supplied pack provenance")

    session = await target_adapter.open_session(validated_compiled.execution_spec)
    session_closed = False
    try:
        turn_result = await session.send(validated_compiled.agent_visible_prompt)
    finally:
        await session.close()
        session_closed = True

    reset = next(
        contract
        for contract in validated_pack.reset_contracts
        if contract.reset_contract_id == case.reset_contract_id
    )
    for step in reset.steps:
        await environment.apply_reset(step)
    reset_digest = await environment.state_digest()
    if reset_digest != reset.baseline_digest:
        raise ValueError("reset did not restore the declared baseline digest")

    suite = next(
        suite for suite in validated_pack.oracle_suites if suite.suite_id == case.oracle_suite_id
    )
    bundle_results: list[ProbeOracleBundleResult] = []
    for bundle in suite.bundles:
        observations: list[ProbeObservation] = []
        for probe in bundle.probes:
            if bundle.category in {
                ProbeOracleCategory.UTILITY,
                ProbeOracleCategory.SECURITY_EFFECT,
            }:
                value = await environment.observe(
                    probe,
                    compiled=validated_compiled,
                    turn_result=turn_result,
                )
            else:
                value = _runtime_observation(
                    bundle.category,
                    compiled=validated_compiled,
                    attack_present=case.attack.attack_present,
                    session_closed=session_closed,
                    reset_digest=reset_digest,
                )
            observations.append(
                ProbeObservation(
                    probe_id=probe.probe_id,
                    category=bundle.category,
                    value=value,
                )
            )
        observations_by_id = {
            observation.probe_id: observation.value for observation in observations
        }
        oracle_results: list[OracleResult] = []
        for oracle in bundle.oracles:
            values = tuple(observations_by_id[probe_id] for probe_id in oracle.probe_ids)
            passed = all(
                _evaluate(oracle.expectation, value, oracle.expected_value) for value in values
            )
            oracle_results.append(
                OracleResult(
                    oracle_id=oracle.oracle_id,
                    category=bundle.category,
                    passed=passed,
                    detail=(
                        "project oracle expectation satisfied"
                        if passed
                        else "project oracle expectation failed"
                    ),
                )
            )
        bundle_results.append(
            ProbeOracleBundleResult(
                category=bundle.category,
                observations=tuple(observations),
                oracle_results=tuple(oracle_results),
                passed=all(result.passed for result in oracle_results),
            )
        )

    return NativeExecutionResult(
        run_id=validated_compiled.execution_spec.run_id,
        pack_id=validated_pack.pack_id,
        case_id=case.case_id,
        session_id=session.session_id,
        target_response=turn_result.response,
        bundle_results=tuple(bundle_results),
        reset_baseline_digest=reset_digest,
        passed=all(bundle.passed for bundle in bundle_results),
    )


__all__ = [
    "NativeExecutionResult",
    "OracleResult",
    "ProbeObservation",
    "ProbeOracleBundleResult",
    "ScenarioEnvironment",
    "execute_compiled_case",
]
