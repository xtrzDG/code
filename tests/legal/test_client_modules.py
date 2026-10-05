"""
Every package under app/clients talks to an outside service. Each one is
either named by a sub-processor entry or excluded with a reason, so a new
client cannot ship without the DPA's list (and the owners' notice) knowing.
"""

from pathlib import Path

from app.registries.legal.subprocessor_registry import SubprocessorRegistry

CLIENTS_DIRECTORY: Path = Path(__file__).resolve().parents[2] / "app" / "clients"


def client_packages() -> set[str]:
    return {
        path.name
        for path in CLIENTS_DIRECTORY.iterdir()
        if path.is_dir() and (path / "__init__.py").exists()
    }


def test_every_client_module_reaches_a_listed_sub_processor_or_none() -> None:
    registry = SubprocessorRegistry()
    named = {
        str(module)
        for entry in registry.list_entries()
        for module in entry.client_modules
    }
    excluded = {
        str(module) for module in registry.client_modules_without_subprocessor()
    }

    missing = client_packages() - named - excluded

    assert missing == set(), (
        f"app/clients/{sorted(missing)} have no sub-processor entry: add one to "
        "app/registries/legal (with its announcement) or an exclusion with a reason"
    )


def test_the_registry_names_only_client_modules_that_exist() -> None:
    registry = SubprocessorRegistry()
    named = {
        str(module)
        for entry in registry.list_entries()
        for module in entry.client_modules
    }
    excluded = {
        str(module) for module in registry.client_modules_without_subprocessor()
    }

    assert (named | excluded) - client_packages() == set()
    assert named & excluded == set()


def test_every_exclusion_says_why() -> None:
    reasons = SubprocessorRegistry().client_modules_without_subprocessor().values()

    assert all(len(str(reason)) > 30 for reason in reasons)
