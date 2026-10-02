from dependency_injector import containers
from dependency_injector.providers import Singleton

from app.schemas.configurations.app_settings import AppSettings
from app.schemas.configurations.example_config import ExampleConfig
from app.utilities.config_helpers.app_settings.app_settings_assembler import get_app_settings
from app.utilities.config_helpers.example_config_assembler import get_example_config


class ConfigContainer(containers.DeclarativeContainer):
    app_settings: Singleton[AppSettings] = Singleton(get_app_settings)
    example_config: Singleton[ExampleConfig] = Singleton(get_example_config)
