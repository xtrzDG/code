"""The base of the dataset models: unknown keys fail loudly."""

from pydantic import BaseModel, ConfigDict


class StrictModel(BaseModel):
    """Dataset models refuse unknown keys, so a typo fails loudly."""

    model_config = ConfigDict(extra="forbid", frozen=True)
