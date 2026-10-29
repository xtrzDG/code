from pathlib import Path

from scripts.export_display_names import export_display_names

GENERATED_MODULE: Path = (
    Path(__file__).resolve().parents[2] / "web/src/lib/displayNames.generated.ts"
)


def test_cabinet_display_names_match_the_backend() -> None:
    assert GENERATED_MODULE.read_text(encoding="utf-8") == export_display_names(), (
        "Run `cd web && npm run gen:names` and commit the result."
    )


def test_italian_names_are_exported() -> None:
    # The server and every browser name countries and languages alike.
    module: str = export_display_names()

    assert '    "GE": "Georgia",\n' in module
    assert '    "DE": "Germania",\n' in module
    assert '    "ru": "russo",\n' in module
    assert '    "he": "ebraico",\n' in module
