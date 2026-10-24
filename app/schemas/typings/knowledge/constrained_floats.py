"""Keep abc order."""

from base_typed_float import BaseConstrainedTypedFloat


class EmbeddingSimilarity(BaseConstrainedTypedFloat):
    """
    Cosine similarity of a query's and a knowledge item's embeddings: 1 the
    same meaning, 0 unrelated, below 0 opposed.

    Example:
        similarity = EmbeddingSimilarity(0.62)
    """

    ge = -1.0
    le = 1.0
