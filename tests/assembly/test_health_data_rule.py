"""
Health details are special-category data (GDPR art. 9): the chat and the
phone instruction both tell the assistant never to ask about health,
conditions, pregnancy, medication or treatments unless the business's rules
need it, and to keep only what the staff need (an allergy) in a booking's
notes, never diagnoses.
"""

import pytest

from app.utilities.assembly.health_data_rule import HEALTH_DATA_RULE
from tests.assembly.georgian_restaurant_seed import seed_georgian_restaurant
from tests.assembly.testbed import AssemblyTestbed


@pytest.mark.parametrize("channel", [0, 1], ids=["chat", "phone"])
def test_the_never_section_keeps_health_details_out(channel: int) -> None:
    testbed = AssemblyTestbed()
    business = seed_georgian_restaurant(testbed)
    version = testbed.assemble(business.id)
    prompt = [str(version.prompt_text), str(version.phone_prompt_text)][channel]

    never = prompt.split("# Never\n")[1].split("\n\n")[0]

    assert HEALTH_DATA_RULE in never
    assert "never diagnoses or other health details" in never
    assert "unless this business's rules say a booking needs it" in never
