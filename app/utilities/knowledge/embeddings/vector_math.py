"""
Cosine similarity of embedding vectors and their pgvector text form.

Vectors are technical values of the embedding model (raw floats); the
similarity leaves as a typed `EmbeddingSimilarity`.
"""

import math
from collections.abc import Sequence

from app.schemas.typings.knowledge.constrained_floats import EmbeddingSimilarity


def cosine_similarity(first: Sequence[float], second: Sequence[float]) -> float:
    """
    Cosine of the angle between two vectors; 0.0 for vectors of different
    lengths or of zero length (nothing in common can be measured).
    """

    if len(first) != len(second) or len(first) == 0:
        return 0.0

    dot: float = math.fsum(
        left * right for left, right in zip(first, second, strict=True)
    )
    first_norm: float = math.sqrt(math.fsum(value * value for value in first))
    second_norm: float = math.sqrt(math.fsum(value * value for value in second))
    if first_norm == 0.0 or second_norm == 0.0:
        return 0.0

    return dot / (first_norm * second_norm)


def to_similarity(value: float) -> EmbeddingSimilarity:
    """A computed cosine as a similarity (rounding past ±1 clamped, NaN as 0)."""

    if math.isnan(value):
        return EmbeddingSimilarity(0.0)

    return EmbeddingSimilarity(min(1.0, max(-1.0, value)))


def vector_literal(vector: Sequence[float]) -> str:
    """The pgvector text form of a vector: "[0.1,-0.2,...]"."""

    return "[" + ",".join(repr(float(value)) for value in vector) + "]"
