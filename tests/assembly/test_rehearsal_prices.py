"""
The rehearsal assistant (LLM_PROVIDER=scripted) names the price of the item
a price-question customer quotes, so the deterministic price check passes on
development, staging and end-to-end servers whatever the item's description.
"""

from app.utilities.llm_rehearsal.rehearsal_facts import find_price

FACTS: str = "\n".join(
    [
        "Facts:",
        "- Product: Khachapuri: Price: 18.00 GEL",
        "- Dish: Badrijani with walnuts: Rolled eggplant; walnut paste; Price: 15.00 GEL; Tags: starters",
        "- Dish: Lobio: Beans in a clay pot",
        "Menu note: Lobio: Price: 99.00 GEL is not a fact row",
    ]
)


def test_the_price_follows_the_title_with_or_without_a_description() -> None:
    assert find_price(FACTS, 'How much does it cost? "Khachapuri" Hello') == "18.00 GEL"
    assert find_price(FACTS, 'Сколько стоит "Badrijani with walnuts"?') == "15.00 GEL"


def test_no_price_without_a_quoted_item_a_price_or_a_fact_row() -> None:
    assert find_price(FACTS, "How much is the khachapuri?") is None
    assert find_price(FACTS, 'How much is "Lobio"?') is None
    assert find_price(FACTS, 'How much is "Pizza"?') is None
