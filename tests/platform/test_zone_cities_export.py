from pathlib import Path

from scripts.export_zone_cities import derived_city, export_zone_cities

GENERATED_MODULE: Path = (
    Path(__file__).resolve().parents[2] / "web/src/lib/zoneCities.generated.ts"
)


def test_cabinet_zone_cities_match_the_backend() -> None:
    assert GENERATED_MODULE.read_text(encoding="utf-8") == export_zone_cities(), (
        "Run `cd web && npm run gen:names` and commit the result."
    )


def test_cities_are_exported_in_georgian_and_russian() -> None:
    # Browsers have no Georgian exemplar cities; the table must.
    module: str = export_zone_cities()

    assert '    "Asia/Tbilisi": "თბილისი",\n' in module
    assert '    "Asia/Tbilisi": "Тбилиси",\n' in module
    assert '    "Europe/Berlin": "Берлин",\n' in module
    # A zone CLDR keys by an older name is found under its alias.
    assert '    "Asia/Kolkata": "Калькутта",\n' in module


def test_english_keeps_only_cities_spelled_differently() -> None:
    module: str = export_zone_cities()

    assert '    "Europe/Kiev": "Kyiv",\n' in module
    assert '"America/New_York": "New York"' not in module
    assert derived_city("America/Argentina/Buenos_Aires") == "Buenos Aires"
