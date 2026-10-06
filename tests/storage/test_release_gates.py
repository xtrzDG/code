"""Storage refuses to write an enum value of a closed release gate."""

import pytest

from app.adapters.storage.persisted_document_codec import PersistedDocumentCodec
from app.schemas.constants.monitoring import PlatformAlertCode
from app.schemas.domain.platform_alerts import PlatformAlertStateDocument
from app.schemas.dto.release_gates import ReleaseGate
from app.schemas.exceptions.storage_errors import ClosedReleaseGateError
from app.schemas.typings.maintenance.constrained_strings import (
    GatedEnumValue,
    ReleaseGateName,
    StoredEnumPath,
)
from app.schemas.typings.storage.constrained_strings import DocumentCollectionName
from app.utilities.storage.release_gates import (
    is_gate_open,
    path_steps,
    refuse_closed_values,
    values_at,
)
from tests.storage.document_evolution.sample_documents import sample_document

ALERTS: DocumentCollectionName = DocumentCollectionName("platform_alert_states")
GATE_NAME: ReleaseGateName = ReleaseGateName("backfill_alert")


def gate(is_open: bool, path: str = "code") -> ReleaseGate:
    return ReleaseGate(
        name=GATE_NAME,
        collection_name=ALERTS,
        path=StoredEnumPath(path),
        values=[GatedEnumValue("backfill_stalled")],
        is_open=is_open,
    )


def alert(code: PlatformAlertCode) -> PlatformAlertStateDocument:
    return sample_document(PlatformAlertStateDocument, ALERTS).model_copy(
        update={"code": code}
    )


def codec(*gates: ReleaseGate) -> PersistedDocumentCodec[PlatformAlertStateDocument]:
    return PersistedDocumentCodec(
        PlatformAlertStateDocument, ALERTS, release_gates=gates
    )


def test_a_closed_gate_keeps_its_values_out_of_storage() -> None:
    closed = codec(gate(is_open=False))

    with pytest.raises(ClosedReleaseGateError, match="backfill_stalled"):
        closed.encode(alert(PlatformAlertCode.BACKFILL_STALLED))
    assert '"dead_jobs"' in closed.encode(alert(PlatformAlertCode.DEAD_JOBS))


def test_an_open_gate_or_another_collection_writes_freely() -> None:
    stalled = alert(PlatformAlertCode.BACKFILL_STALLED)
    elsewhere = PersistedDocumentCodec(
        PlatformAlertStateDocument,
        DocumentCollectionName("notes"),
        release_gates=[gate(is_open=False)],
    )

    assert '"backfill_stalled"' in codec(gate(is_open=True)).encode(stalled)
    assert '"backfill_stalled"' in elsewhere.encode(stalled)
    # Reads are never gated: the release that closes a gate knows the value.
    assert codec(gate(is_open=False)).decode(codec().encode(stalled)) == stalled


def test_paths_reach_into_lists_and_mappings() -> None:
    document = {
        "results": [{"kinds": ["a", "b"]}, {"kinds": ["c"]}, {"other": 1}],
        "by_language": {"en": {"kind": "d"}, "ka": {"kind": "e"}},
        "kind": "f",
    }

    assert path_steps(StoredEnumPath("results[].kinds[]")) == (
        "results",
        "[]",
        "kinds",
        "[]",
    )
    assert list(
        values_at(document, path_steps(StoredEnumPath("results[].kinds[]")))
    ) == [
        "a",
        "b",
        "c",
    ]
    assert list(
        values_at(document, path_steps(StoredEnumPath("by_language{}.kind")))
    ) == [
        "d",
        "e",
    ]
    assert list(values_at(document, path_steps(StoredEnumPath("missing[]")))) == []
    with pytest.raises(ClosedReleaseGateError):
        refuse_closed_values(
            document, [(("by_language", "{}", "kind"), frozenset({"e"}))]
        )
    refuse_closed_values(document, [(("kind",), frozenset({"a"}))])


def test_writers_ask_whether_a_gate_is_open() -> None:
    assert is_gate_open(GATE_NAME, [gate(is_open=True)]) is True
    assert is_gate_open(GATE_NAME, [gate(is_open=False)]) is False
    assert is_gate_open(ReleaseGateName("unknown_gate"), [gate(is_open=True)]) is False
