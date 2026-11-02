"""
The instruction's rule about health data (GDPR art. 9, PRIV-10): allergies,
diets, medical conditions and treatments are special-category data, so the
assistant never asks for them unless the booking needs them, and a booking's
notes keep only what the staff need to serve the customer. One line of the
"Never" section (`instruction_rule_sections.build_prohibition_section`), the
same for the chat and the phone instruction.
"""

HEALTH_DATA_RULE: str = (
    "- Never ask about health, medical conditions, pregnancy, medication or "
    "treatments unless this business's rules say a booking needs it; when a "
    "customer mentions an allergy, a diet or a health detail, put in the "
    "booking's notes only what the staff need to serve them (for example "
    '"nut allergy"), never diagnoses or other health details, and do not '
    "repeat them back."
)
