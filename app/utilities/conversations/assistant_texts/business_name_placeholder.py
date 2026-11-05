"""
The business name inside the assistant's fixed texts.

`{business}` is replaced with the business name (never with str.format, so
braces in a name are harmless).
"""

BUSINESS_PLACEHOLDER: str = "{business}"


def fill_business_name(template: str, business_name: str) -> str:
    """Insert the business name into a resolved template."""

    return template.replace(BUSINESS_PLACEHOLDER, business_name)
