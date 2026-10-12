"""
The widget script's photos, voice messages and thumbs agree with the API:
the paths, the attachment limit, the recording formats, the rating
reasons and a text in every interface language.
"""

import json
import re
import shutil
import subprocess

import pytest

from app.gateways.http.widget_attachment_routes import WIDGET_ATTACHMENTS_PATH
from app.gateways.http.widget_rating_routes import WIDGET_RATING_PATH
from app.schemas.constants.conversations import ConversationRatingReason
from app.schemas.dto.channels.widget import MAX_MESSAGE_ATTACHMENTS
from app.schemas.typings.media.prefixed_id import WidgetUploadId
from app.utilities.media.upload_checks import UPLOAD_AUDIO_TYPES, UPLOAD_IMAGE_TYPES
from tests.channels.test_widget_script import read_script_constant, read_script_number
from tests.channels.widget_script_source import SCRIPT_SOURCE


def read_script_list(name: str) -> list[str]:
    match = re.search(rf"var {name} = (\[[^\]]*\]);", SCRIPT_SOURCE)
    assert match is not None, name
    values: list[str] = json.loads(match.group(1))
    return values


def read_text_blocks(opening: str) -> dict[str, set[str]]:
    """The languages of one texts object of the script and each one's keys."""

    block: str = SCRIPT_SOURCE[SCRIPT_SOURCE.index(opening) :]
    block = block[: block.index("\n  };")]
    return {
        match.group(1): set(re.findall(r"\n      ([A-Za-z]+):", match.group(2)))
        for match in re.finditer(r"\n    ([a-z]+): \{(.*?)\n    \}", block, re.S)
    }


class TestTheScriptAgreesWithTheApi:
    def test_paths_and_the_attachment_limit(self) -> None:
        assert read_script_constant("ATTACHMENTS_PATH") == WIDGET_ATTACHMENTS_PATH
        assert read_script_constant("RATING_PATH") == WIDGET_RATING_PATH
        assert read_script_number("MAX_ATTACHMENTS") == MAX_MESSAGE_ATTACHMENTS

    def test_the_upload_ids_it_accepts_are_the_apis(self) -> None:
        match = re.search(r"var ATTACHMENT_ID_PATTERN = /(.*)/;", SCRIPT_SOURCE)
        assert match is not None

        assert re.fullmatch(match.group(1), str(WidgetUploadId()))

    def test_it_records_only_formats_the_api_takes(self) -> None:
        bases = {kind.split(";")[0] for kind in read_script_list("RECORDING_TYPES")}

        assert bases <= set(UPLOAD_AUDIO_TYPES)
        assert "image/jpeg" in UPLOAD_IMAGE_TYPES

    def test_the_reasons_are_the_apis_in_its_order(self) -> None:
        reasons = read_script_list("RATING_REASONS")
        reason_texts = read_script_list("RATING_REASON_TEXTS")

        assert reasons == [reason.value for reason in ConversationRatingReason]
        assert len(reason_texts) == len(reasons)


class TestMediaTexts:
    def test_every_interface_language_has_every_media_text(self) -> None:
        interface = read_text_blocks("var TEXTS = {")
        media = read_text_blocks("var MEDIA_TEXTS = {")
        english = media["en"]

        assert set(media) == set(interface)
        assert sorted(tag for tag, keys in media.items() if keys != english) == []
        assert set(read_script_list("RATING_REASON_TEXTS")) <= english
        # Media texts add to the interface texts, never replace one.
        assert english.isdisjoint(interface["en"])


def run_node(program: str) -> str:
    node = shutil.which("node")
    assert node is not None
    result = subprocess.run(
        [node, "-e", program], capture_output=True, text=True, timeout=60, check=False
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def script_function(name: str) -> str:
    match = re.search(rf"\n  function {name}\(.*?\n  \}}\n", SCRIPT_SOURCE, re.S)
    assert match is not None, name
    return match.group(0)


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_a_stored_message_keeps_only_well_formed_attachments() -> None:
    upload_id = str(WidgetUploadId())
    stored = [
        {"id": upload_id, "kind": "audio", "seconds": 8.6, "url": "blob:x"},
        {"id": "widget_upload_../../x", "kind": "image"},
        {"id": upload_id, "kind": "video"},
        *[{"id": upload_id, "kind": "image"} for _ in range(5)],
    ]
    program = (
        f"var ATTACHMENT_ID_PATTERN = {_pattern()};\nvar MAX_ATTACHMENTS = 4;\n"
        f"{script_function('readAttachments')}\n"
        f"console.log(JSON.stringify(readAttachments({json.dumps(stored)})));"
    )

    kept = json.loads(run_node(program))

    assert kept[0] == {"id": upload_id, "kind": "audio", "seconds": 9}
    assert len(kept) == 4
    assert all(item["kind"] == "image" for item in kept[1:])


def _pattern() -> str:
    match = re.search(r"var ATTACHMENT_ID_PATTERN = (/.*/);", SCRIPT_SOURCE)
    assert match is not None
    return match.group(1)
