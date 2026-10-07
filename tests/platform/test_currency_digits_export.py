from pathlib import Path

from scripts.export_currency_digits import export_currency_digits

GENERATED_MODULE: Path = (
    Path(__file__).resolve().parents[2] / "web/src/lib/currencyDigits.generated.ts"
)


def test_cabinet_currency_digits_match_the_backend() -> None:
    assert GENERATED_MODULE.read_text(encoding="utf-8") == export_currency_digits(), (
        "Run `cd web && npm run gen:currencies` and commit the result."
    )


def test_currencies_with_unusual_digits_are_exported() -> None:
    module: str = export_currency_digits()

    assert "  JPY: 0,\n" in module
    assert "  KWD: 3,\n" in module
    assert "  USD: 2,\n" in module
