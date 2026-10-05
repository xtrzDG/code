"""
The rehearsal assistant's knowledge (LLM_PROVIDER=scripted): when the
customer asks a question the fact table answers ("- Question: <title>:
<answer>" and "- Policy: <title>: <text>" rows of its instruction), it
answers with that text, so an owner's corrected answer and the check
saved from it pass on a development, staging or end-to-end server.
"""

import re

from app.utilities.knowledge.search_text import fold_words

ANSWER_ROW_PREFIXES: tuple[str, ...] = ("- Question: ", "- Policy: ")
QUOTED_ITEM_PATTERN: re.Pattern[str] = re.compile(r'"([^"]+)"')
PRICE_LABEL: str = "Price: "
PRICE_END: str = ";"
LABEL_SEPARATOR: str = ": "


def find_fact_answer(system_prompt: str, customer_text: str) -> str | None:
    """
    The text of the fact row whose title is the customer's question
    (ignoring case, accents and punctuation), or None.
    """

    question: str = fold_words(customer_text)
    if question == "":
        return None

    for line in system_prompt.splitlines():
        prefix: str | None = next(
            (prefix for prefix in ANSWER_ROW_PREFIXES if line.startswith(prefix)),
            None,
        )
        if prefix is None:
            continue

        row: str = line[len(prefix) :]
        start: int = 0
        while (separator := row.find(LABEL_SEPARATOR, start)) != -1:
            if fold_words(row[:separator]) == question:
                return row[separator + len(LABEL_SEPARATOR) :].strip() or None

            start = separator + 1

    return None


def find_price(system_prompt: str, customer_text: str) -> str | None:
    """
    The price of the item the customer names in quotes, as its fact row
    gives it ("- Product: Khachapuri: Price: 18.00 GEL" -> "18.00 GEL").
    """

    quoted: re.Match[str] | None = QUOTED_ITEM_PATTERN.search(customer_text)
    if quoted is None:
        return None

    marker: str = f": {quoted.group(1)}: {PRICE_LABEL}"
    for line in system_prompt.splitlines():
        start: int = line.find(marker)
        if line.startswith("- ") and start != -1:
            price: str = line[start + len(marker) :]
            return price.split(PRICE_END)[0].strip() or None

    return None
