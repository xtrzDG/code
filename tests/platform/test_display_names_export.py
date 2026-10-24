from pathlib import Path

from scripts.export_display_names import export_display_names

GENERATED_MODULE: Path = (
    Path(__file__).resolve().parents[2] / "web/src/lib/displayNames.generated.ts"
)


def test_cabinet_display_names_match_the_backend() -> None:
    assert GENERATED_MODULE.read_text(encoding="utf-8") == export_display_names(), (
        "Run `cd web && npm run gen:names` and commit the result."
    )


def test_georgian_names_are_exported() -> None:
    # Chrome has no Georgian display names; the table must.
    module: str = export_display_names()

    assert '    "GE": "საქართველო",\n' in module
    assert '    "DE": "გერმანია",\n' in module
    assert '    "ru": "რუსული",\n' in module
    assert '    "he": "ებრაული",\n' in module
