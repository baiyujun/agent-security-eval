from __future__ import annotations

import pytest
from pydantic import ValidationError

from agentsec_eval.scenario_assets import (
    NativeScenarioPack,
    pack_content_digest,
    validate_pack,
    with_computed_digest,
)

from .test_models import make_complete_pack


def test_validate_pack_accepts_complete_pack_and_returns_fresh_immutable_model() -> None:
    pack = with_computed_digest(make_complete_pack())

    validated = validate_pack(pack)

    assert validated == pack
    assert validated is not pack
    with pytest.raises(ValidationError, match="frozen"):
        validated.pack_id = "changed"


def test_pack_digest_is_canonical_and_rejects_tampering() -> None:
    first = with_computed_digest(make_complete_pack())
    second = with_computed_digest(NativeScenarioPack.model_validate(first.model_dump(mode="json")))
    tampered = first.model_copy(update={"pack_version": "1.0.1"})

    assert first.output_digest == second.output_digest == pack_content_digest(first)
    with pytest.raises(ValueError, match="output_digest"):
        validate_pack(tampered)


@pytest.mark.parametrize(
    ("collection", "field", "bad_value", "message"),
    [
        ("cases", "normal_task_id", "task.missing", "normal task"),
        ("cases", "environment_id", "env.missing", "environment"),
        ("cases", "authorization_context_id", "auth.missing", "authorization"),
        ("cases", "oracle_suite_id", "suite.missing", "oracle suite"),
        ("cases", "reset_contract_id", "reset.missing", "reset contract"),
        ("base_scenarios", "family_id", "family.missing", "family"),
    ],
)
def test_validate_pack_rejects_broken_cross_references(
    collection: str, field: str, bad_value: str, message: str
) -> None:
    pack = make_complete_pack()
    item = getattr(pack, collection)[0].model_copy(update={field: bad_value})
    broken = pack.model_copy(update={collection: (item,)})
    broken = broken.model_copy(update={"output_digest": pack_content_digest(broken)})

    with pytest.raises(ValueError, match=message):
        validate_pack(broken)


def test_validate_pack_revalidates_model_copy_bypasses() -> None:
    pack = with_computed_digest(make_complete_pack())
    invalid_attack = pack.cases[0].attack.model_copy(update={"seed_id": None})
    invalid_case = pack.cases[0].model_copy(update={"attack": invalid_attack})
    bypassed = pack.model_copy(update={"cases": (invalid_case,)})
    bypassed = bypassed.model_copy(update={"output_digest": pack_content_digest(bypassed)})

    with pytest.raises(ValidationError, match="complete attack references"):
        validate_pack(bypassed)


def test_validate_pack_rejects_private_fixture_in_agent_visible_case_inputs() -> None:
    pack = make_complete_pack()
    private_fixture_id = "fixture.private-verifier"
    case = pack.cases[0].model_copy(
        update={"fixture_ids": (*pack.cases[0].fixture_ids, private_fixture_id)}
    )
    broken = pack.model_copy(update={"cases": (case,)})
    broken = broken.model_copy(update={"output_digest": pack_content_digest(broken)})

    with pytest.raises(ValueError, match="private fixture"):
        validate_pack(broken)


def test_validate_pack_requires_component_evidence_to_resolve() -> None:
    pack = make_complete_pack()
    family = pack.family.model_copy(
        update={
            "evidence": pack.family.evidence.model_copy(
                update={"provenance_ids": ("prov.missing",)}
            )
        }
    )
    broken = pack.model_copy(update={"family": family})
    broken = broken.model_copy(update={"output_digest": pack_content_digest(broken)})

    with pytest.raises(ValueError, match="provenance"):
        validate_pack(broken)


def test_validate_pack_rejects_capability_not_authorized_for_case() -> None:
    pack = make_complete_pack()
    authorization = pack.authorization_contexts[0].model_copy(
        update={"allowed_capability_ids": ("cap.other",)}
    )
    broken = pack.model_copy(update={"authorization_contexts": (authorization,)})
    broken = broken.model_copy(update={"output_digest": pack_content_digest(broken)})

    with pytest.raises(ValueError, match="not authorized"):
        validate_pack(broken)


def test_validate_pack_rejects_duplicate_component_identity() -> None:
    pack = make_complete_pack()
    broken = pack.model_copy(update={"cases": (pack.cases[0], pack.cases[0])})
    broken = broken.model_copy(update={"output_digest": pack_content_digest(broken)})

    with pytest.raises(ValueError, match="duplicate case_id"):
        validate_pack(broken)
