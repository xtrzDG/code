"""
Processor uses: each flow of personal data to an outside provider, the
settings that choose its provider, what it sends, and the flows whose
provider the sub-processor list does not cover.
"""

from base_pydantic_schemas import ImmutableDTO
from pydantic import Field

from app.schemas.constants.legal import ProcessorDataCategory, ProcessorFlow
from app.schemas.typings.legal.constrained_strings import ClientModuleName
from app.schemas.typings.legal.strings import ProcessorUseDescription
from app.schemas.typings.platform.constrained_strings import EnvironmentVariableName


class ProcessorUse(ImmutableDTO):
    """
    One data flow as the processor use registry declares it: the settings
    that choose its provider (`provider_settings`, the first one decides),
    the categories of data it sends and what it is for.
    """

    flow: ProcessorFlow
    provider_settings: list[EnvironmentVariableName] = Field(
        default_factory=list[EnvironmentVariableName]
    )
    data_categories: list[ProcessorDataCategory] = Field(
        default_factory=list[ProcessorDataCategory]
    )
    description: ProcessorUseDescription


class ConfiguredProcessorUse(ImmutableDTO):
    """
    Where this deployment's settings send one flow: the `app/clients`
    package of the provider (None when the flow is off or stays offline).
    """

    use: ProcessorUse
    client_module: ClientModuleName | None = None


class UncoveredProcessorUse(ImmutableDTO):
    """
    A configured flow whose provider no sub-processor entry in force covers:
    what it would send and the settings that send it there.
    """

    flow: ProcessorFlow
    client_module: ClientModuleName
    data_categories: list[ProcessorDataCategory] = Field(
        default_factory=list[ProcessorDataCategory]
    )
    provider_settings: list[EnvironmentVariableName] = Field(
        default_factory=list[EnvironmentVariableName]
    )
