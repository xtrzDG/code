import threading
from pathlib import Path

from pydantic import ValidationError

from app.contracts.llm_cassettes import LlmCassetteStoreAdapterContract
from app.schemas.constants.assistants import AssistantToolName
from app.schemas.dto.llm_cassettes import (
    LlmCassetteEntry,
    LlmCassetteFile,
    LlmCassetteInstruction,
    LlmCassetteRecording,
    LlmCassetteRequest,
    LlmCassetteTake,
    LlmCassetteToolSet,
)
from app.schemas.exceptions.application_errors import ValidationFailedError
from app.schemas.typings.assistants.strings import SystemPromptText
from app.schemas.typings.evaluations.constrained_integers import (
    LlmCassetteFormatVersion,
)
from app.schemas.typings.evaluations.constrained_strings import (
    LlmInstructionDigest,
    LlmRequestDigest,
    LlmToolsDigest,
)

CASSETTE_FORMAT_VERSION: LlmCassetteFormatVersion = LlmCassetteFormatVersion(1)


class LlmCassetteFileStore(LlmCassetteStoreAdapterContract):
    """
    A cassette in one JSON file (evals/cassettes/<niche>.json): read into
    memory when the store is made, written back by `save`. `is_fresh`
    starts empty even when the file exists, so a re-recording keeps only
    what the current datasets still ask. The file is written with sorted
    lists and indentation, so a re-recording shows up as a readable diff.
    """

    def __init__(self, path: Path, is_fresh: bool = False) -> None:
        self._path: Path = path
        self._lock: threading.Lock = threading.Lock()
        stored: LlmCassetteFile = (
            LlmCassetteFile(format_version=CASSETTE_FORMAT_VERSION)
            if is_fresh or not path.exists()
            else read_cassette_file(path)
        )
        self._recording: LlmCassetteRecording | None = stored.recording
        self._instructions: dict[LlmInstructionDigest, SystemPromptText] = {
            instruction.digest: instruction.text for instruction in stored.instructions
        }
        self._tool_sets: dict[LlmToolsDigest, list[AssistantToolName]] = {
            tool_set.digest: list(tool_set.tool_names) for tool_set in stored.tool_sets
        }
        self._entries: dict[LlmRequestDigest, LlmCassetteEntry] = {
            entry.request.request_digest: entry for entry in stored.entries
        }

    def recording(self) -> LlmCassetteRecording | None:
        return self._recording

    def set_recording(self, recording: LlmCassetteRecording) -> None:
        self._recording = recording

    def find(self, request_digest: LlmRequestDigest) -> LlmCassetteEntry | None:
        return self._entries.get(request_digest)

    def list_entries(self) -> list[LlmCassetteEntry]:
        with self._lock:
            return list(self._entries.values())

    def record(self, request: LlmCassetteRequest, take: LlmCassetteTake) -> None:
        with self._lock:
            entry: LlmCassetteEntry | None = self._entries.get(request.request_digest)
            takes: list[LlmCassetteTake] = [
                kept
                for kept in ([] if entry is None else entry.takes)
                if kept.sample_index != take.sample_index
            ]
            takes.append(take)
            self._entries[request.request_digest] = LlmCassetteEntry(
                request=request,
                takes=sorted(takes, key=lambda kept: int(kept.sample_index)),
            )

    def remember_instruction(
        self, digest: LlmInstructionDigest, text: SystemPromptText
    ) -> None:
        with self._lock:
            self._instructions[digest] = text

    def read_instruction(self, digest: LlmInstructionDigest) -> SystemPromptText | None:
        return self._instructions.get(digest)

    def remember_tools(
        self, digest: LlmToolsDigest, tool_names: list[AssistantToolName]
    ) -> None:
        with self._lock:
            self._tool_sets[digest] = list(tool_names)

    def read_tools(self, digest: LlmToolsDigest) -> list[AssistantToolName] | None:
        return self._tool_sets.get(digest)

    def save(self) -> None:
        with self._lock:
            stored = LlmCassetteFile(
                format_version=CASSETTE_FORMAT_VERSION,
                recording=self._recording,
                instructions=[
                    LlmCassetteInstruction(digest=digest, text=text)
                    for digest, text in sorted(self._instructions.items())
                ],
                tool_sets=[
                    LlmCassetteToolSet(digest=digest, tool_names=names)
                    for digest, names in sorted(self._tool_sets.items())
                ],
                entries=[entry for _, entry in sorted(self._entries.items())],
            )

        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(stored.model_dump_json(indent=1) + "\n", encoding="utf-8")


def read_cassette_file(path: Path) -> LlmCassetteFile:
    """
    A stored cassette.

    Raises:
        ValidationFailedError: the file is not a cassette of this format.
    """

    try:
        stored: LlmCassetteFile = LlmCassetteFile.model_validate_json(
            path.read_text(encoding="utf-8")
        )
    except ValidationError as error:
        raise ValidationFailedError(
            f"{path} is not a readable cassette: {error.error_count()} problem(s)."
        ) from error

    if stored.format_version != CASSETTE_FORMAT_VERSION:
        raise ValidationFailedError(
            f"{path} has cassette format {stored.format_version}; this code reads "
            f"format {CASSETTE_FORMAT_VERSION}. Record the cassettes again."
        )

    return stored
