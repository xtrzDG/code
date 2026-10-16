"""
The boxes of an ISO base media file (MP4, M4A), read by their sizes.

Every box must fit inside its parent; a reader that is lenient here could
see other boxes than a decoder does, so a box that runs past its parent,
and a box read once that appears twice, refuse the file.
"""

import struct
from collections.abc import Iterator
from dataclasses import dataclass

HEADER_BYTES: int = 8
LARGE_HEADER_BYTES: int = 16
LARGE_SIZE: int = 1
TO_THE_END: int = 0
FULL_BOX_HEADER_BYTES: int = 4
# A recording's top level holds a few boxes and a fragment pair per slice
# of it; far more is not a voice note.
MOST_TOP_LEVEL_BOXES: int = 20_000


class Mp4StructureError(ValueError):
    """The bytes are not an MP4 structure this reader walks."""


@dataclass(frozen=True)
class Mp4Box:
    """A box's type and where it, its data and its end are in the file."""

    kind: bytes
    start: int
    data_start: int
    end: int


def top_level_boxes(content: bytes) -> list[Mp4Box]:
    """The file's top-level boxes, which must cover it to its last byte."""

    boxes: list[Mp4Box] = []
    for box in iterate_boxes(content, 0, len(content)):
        boxes.append(box)
        if len(boxes) > MOST_TOP_LEVEL_BOXES:
            raise Mp4StructureError("Too many boxes for a voice note.")

    return boxes


def iterate_boxes(content: bytes, start: int, end: int) -> Iterator[Mp4Box]:
    """The boxes from `start` to `end`, each inside those bounds."""

    position: int = start
    while position < end:
        if position + HEADER_BYTES > end:
            raise Mp4StructureError("A box header is cut short.")

        size, kind = struct.unpack_from(">I4s", content, position)
        header: int = HEADER_BYTES
        if size == LARGE_SIZE:
            if position + LARGE_HEADER_BYTES > end:
                raise Mp4StructureError("A box header is cut short.")
            (size,) = struct.unpack_from(">Q", content, position + HEADER_BYTES)
            header = LARGE_HEADER_BYTES
        elif size == TO_THE_END:
            size = end - position

        if size < header or position + size > end:
            raise Mp4StructureError("A box runs past its parent.")

        yield Mp4Box(
            kind=kind, start=position, data_start=position + header, end=position + size
        )
        position += size


def child_boxes(content: bytes, parent: Mp4Box, kind: bytes) -> list[Mp4Box]:
    """The children of `parent` of one type, in order."""

    return [
        box
        for box in iterate_boxes(content, parent.data_start, parent.end)
        if box.kind == kind
    ]


def only_child(content: bytes, parent: Mp4Box, kind: bytes) -> Mp4Box | None:
    """The one child of a type; a second one refuses the file."""

    found: list[Mp4Box] = child_boxes(content, parent, kind)
    if len(found) > 1:
        raise Mp4StructureError(f"Two {kind!r} boxes where one belongs.")

    return found[0] if found else None


def required_child(content: bytes, parent: Mp4Box, kind: bytes) -> Mp4Box:
    """The one child of a type that must be there."""

    found: Mp4Box | None = only_child(content, parent, kind)
    if found is None:
        raise Mp4StructureError(f"A {kind!r} box is missing.")

    return found


def full_box_fields(content: bytes, box: Mp4Box) -> tuple[int, int, int]:
    """A full box's version, its flags and where its fields begin."""

    if box.data_start + FULL_BOX_HEADER_BYTES > box.end:
        raise Mp4StructureError("A full box is cut short.")

    (header,) = struct.unpack_from(">I", content, box.data_start)
    return header >> 24, header & 0xFFFFFF, box.data_start + FULL_BOX_HEADER_BYTES


def read_fields(content: bytes, box: Mp4Box, layout: str, at: int) -> tuple[int, ...]:
    """Big-endian fields of `layout` at `at`, which must lie inside the box."""

    if at + struct.calcsize(layout) > box.end:
        raise Mp4StructureError(f"A {box.kind!r} box is cut short.")

    return struct.unpack_from(layout, content, at)


def read_versioned_fields(
    content: bytes, box: Mp4Box, layouts: dict[int, str]
) -> tuple[int, int]:
    """Two fields of a full box whose layout depends on its version."""

    version, _, at = full_box_fields(content, box)
    if version not in layouts:
        raise Mp4StructureError(f"An unknown {box.kind!r} version.")

    first, second = read_fields(content, box, layouts[version], at)
    return first, second
