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
    gives it after the title and any description ("- Product: Khachapuri:
    Cheese bread; Price: 18.00 GEL; Tags: bakery" -> "18.00 GEL").
    """

    quoted: re.Match[str] | None = QUOTED_ITEM_PATTERN.search(customer_text)
    if quoted is None:
        return None

    title: str = f": {quoted.group(1)}: "
    for line in system_prompt.splitlines():
        start: int = line.find(title)
        if not line.startswith("- ") or start == -1:
            continue

        details: str = line[start + len(title) :]
        price_at: int = details.find(PRICE_LABEL)
        if price_at != -1:
            price: str = details[price_at + len(PRICE_LABEL) :]
            return price.split(PRICE_END)[0].strip() or None

    return None
