from enum import StrEnum


class DeploymentEnvironment(StrEnum):
    """Runtime environment of the backend."""

    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"
