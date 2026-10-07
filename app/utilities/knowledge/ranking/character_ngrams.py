"""Character n-gram overlap of two folded strings, for typos in names."""

from app.utilities.knowledge.search_text import is_space_less_character


def character_ngram_dice(first: str, second: str) -> float:
    """
    Dice coefficient of character n-grams of two folded strings.

    Trigrams for spaced scripts, bigrams when a string contains a space-less
    script (Chinese, Japanese, Thai...), where single words are short.
    """

    has_space_less_text: bool = any(
        is_space_less_character(character) for character in first + second
    )
    size: int = 2 if has_space_less_text else 3
    first_ngrams: list[str] = character_ngrams(first, size)
    second_ngrams: list[str] = character_ngrams(second, size)
    if first_ngrams == [] or second_ngrams == []:
        return 0.0

    remaining: list[str] = list(second_ngrams)
    shared_count: int = 0
    for ngram in first_ngrams:
        if ngram in remaining:
            remaining.remove(ngram)
            shared_count += 1

    return 2.0 * shared_count / (len(first_ngrams) + len(second_ngrams))


def character_ngrams(text: str, size: int) -> list[str]:
    padded: str = f" {text} "
    if len(padded) < size:
        return []

    return [padded[index : index + size] for index in range(len(padded) - size + 1)]
