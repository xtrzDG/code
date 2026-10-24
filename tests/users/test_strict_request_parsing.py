"""The one JSON-body stack of the HTTP layer (strict_request_parsing)."""

from typing import Annotated, Any

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.gateways.http.error_responses import install_error_handlers
from app.gateways.http.strict_request_parsing import (
    build_json_body_dependency,
    describe_json_body,
    inline_local_references,
    parse_json_body,
    parse_path_identifier,
)
from app.schemas.constants.niches import ProfileWizardStep
from app.schemas.dto.billing_cabinet import StartTrialRequest
from app.schemas.dto.knowledge_admin import KnowledgeItemPatch
from app.schemas.dto.profiles.profile_steps import (
    ChannelsStepInput,
    OfferStepInput,
)
from app.schemas.exceptions.application_errors import (
    NotFoundError,
    ValidationFailedError,
)
from app.schemas.typings.businesses.prefixed_id import BusinessId

ADDRESS_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {"city": {"type": "string"}},
}
CONTACT_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {"address": ADDRESS_SCHEMA},
}

read_patch = build_json_body_dependency(KnowledgeItemPatch)
read_trial = build_json_body_dependency(StartTrialRequest, optional=True)


def build_client() -> TestClient:
    application = FastAPI()
    install_error_handlers(application)

    @application.post("/patch")
    def accept_patch(
        body: Annotated[KnowledgeItemPatch, Depends(read_patch)],
    ) -> dict[str, list[str]]:
        return {"fields": sorted(body.model_fields_set)}

    @application.post("/trial")
    def accept_trial(
        body: Annotated[StartTrialRequest, Depends(read_trial)],
    ) -> dict[str, str]:
        return {"billing_period": str(body.billing_period)}

    return TestClient(application)


def test_local_references_are_inlined_and_other_references_kept() -> None:
    definitions: dict[str, object] = {
        "Address": ADDRESS_SCHEMA,
        "Contact": {
            "type": "object",
            "properties": {"address": {"$ref": "#/$defs/Address"}},
        },
    }
    schema: dict[str, object] = {
        "properties": {
            "contacts": {"type": "array", "items": {"$ref": "#/$defs/Contact"}},
            "primary": {"$ref": "#/$defs/Contact", "description": "Main contact"},
            "external": {"$ref": "https://example.com/schema.json"},
        }
    }

    assert inline_local_references(schema, definitions) == {
        "properties": {
            "contacts": {"type": "array", "items": CONTACT_SCHEMA},
            "primary": CONTACT_SCHEMA | {"description": "Main contact"},
            "external": {"$ref": "https://example.com/schema.json"},
        }
    }


def test_json_bodies_are_validated_in_json_mode() -> None:
    patch = parse_json_body(KnowledgeItemPatch, b'{"kind": "faq", "body": null}')

    assert patch.kind == "faq"
    assert patch.model_fields_set == {"kind", "body"}
    with pytest.raises(ValidationFailedError, match="kind"):
        parse_json_body(KnowledgeItemPatch, b'{"kind": "spaceship"}')
    with pytest.raises(ValidationFailedError, match="JSON object"):
        parse_json_body(KnowledgeItemPatch, b"  ")
    with pytest.raises(ValidationFailedError, match="Invalid request"):
        parse_json_body(KnowledgeItemPatch, b"{not json")


def test_optional_bodies_treat_an_empty_body_as_all_defaults() -> None:
    assert parse_json_body(StartTrialRequest, b" \n", optional=True) == (
        StartTrialRequest()
    )
    with pytest.raises(ValidationFailedError, match="billing_period"):
        parse_json_body(
            StartTrialRequest,
            b'{"billing_period": "weekly"}',
            optional=True,
        )


def test_validation_errors_do_not_echo_submitted_values() -> None:
    with pytest.raises(ValidationFailedError) as raised:
        parse_json_body(KnowledgeItemPatch, b'{"kind": "secret-value-123"}')

    assert "secret-value-123" not in str(raised.value)


def test_dependencies_answer_422_for_bad_bodies_and_accept_good_ones() -> None:
    client = build_client()

    accepted = client.post("/patch", content=b'{"title": "Menu"}')
    empty = client.post("/patch", content=b"")
    wrong = client.post("/patch", content=b'{"kind": 5}')
    defaults = client.post("/trial", content=b"")
    chosen = client.post("/trial", content=b'{"billing_period": "annual"}')

    assert accepted.status_code == 200
    assert accepted.json() == {"fields": ["title"]}
    assert empty.status_code == 422
    assert wrong.status_code == 422
    assert defaults.json() == {"billing_period": "monthly"}
    assert chosen.json() == {"billing_period": "annual"}


def test_describe_json_body_inlines_models_and_marks_optional_bodies() -> None:
    required: dict[str, Any] = describe_json_body(KnowledgeItemPatch)
    optional: dict[str, Any] = describe_json_body(StartTrialRequest, optional=True)
    schema: dict[str, Any] = required["requestBody"]["content"]["application/json"][
        "schema"
    ]

    assert required["requestBody"]["required"] is True
    assert optional["requestBody"]["required"] is False
    assert schema["title"] == "KnowledgeItemPatch"
    assert "$defs" not in schema
    assert "$ref" not in str(schema)


def test_several_body_types_become_one_of() -> None:
    description: dict[str, Any] = describe_json_body(OfferStepInput, ChannelsStepInput)
    schema: dict[str, Any] = description["requestBody"]["content"]["application/json"][
        "schema"
    ]

    assert [option["title"] for option in schema["oneOf"]] == [
        "OfferStepInput",
        "ChannelsStepInput",
    ]
    assert "$ref" not in str(schema)
    with pytest.raises(ValueError, match="at least one"):
        describe_json_body()


def test_path_values_become_typed_or_not_found_without_echo() -> None:
    business_id = BusinessId()

    assert parse_path_identifier(str(business_id), BusinessId, "Business") == (
        business_id
    )
    assert parse_path_identifier("offer", ProfileWizardStep, "Wizard step") == (
        ProfileWizardStep.OFFER
    )
    with pytest.raises(NotFoundError, match=r"^Business was not found\.$"):
        parse_path_identifier("not-an-id", BusinessId, "Business")


def test_self_referencing_request_schemas_are_refused() -> None:
    definitions: dict[str, object] = {
        "Node": {"properties": {"child": {"$ref": "#/$defs/Node"}}},
    }

    with pytest.raises(ValueError, match="refers to itself"):
        inline_local_references({"$ref": "#/$defs/Node"}, definitions)
