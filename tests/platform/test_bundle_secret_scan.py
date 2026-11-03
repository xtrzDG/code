"""
No secret ships in the cabinet's build (WEB-05): CI scans the build right
after `next build` in the job that keeps it for the end-to-end shards, for
the key shapes of the platform's providers and the values of the secret
variables (web/scripts/bundle-secrets.mjs, tested by
web/src/test/bundleSecrets.test.ts), and the proxy drops the header of the
middleware bypass (CVE-2025-29927) from every request it forwards
(web/src/proxy.subrequest.test.ts, e2e/security.spec.ts).
"""

from tests.platform.environment_sources import ROOT
from tests.platform.test_supply_chain_workflows import steps, workflow

WEB = ROOT / "web"
RULES = WEB / "scripts" / "bundle-secrets.mjs"
SCANNER = WEB / "scripts" / "scan-bundle-secrets.mjs"
# The key prefixes the readiness item names, as the rules write them.
REQUIRED_SHAPES: tuple[str, ...] = (
    r"[rs]k_(?:live|test)_",
    "whsec_",
    "xi-api-key",
    "AKIA",
    "-----BEGIN",
    "awk_",
)


def test_the_build_is_scanned_right_after_it_is_made() -> None:
    job = workflow("ci.yml")["jobs"]["web-build"]
    names = [str(step.get("name", "")) for step in steps(job)]
    scan = steps(job)[names.index("No secrets in the build")]

    assert names.index("No secrets in the build") == names.index("Build") + 1
    assert job["defaults"]["run"]["working-directory"] == "web"
    assert str(scan["run"]).startswith(
        "node scripts/scan-bundle-secrets.mjs --build .next"
    )
    assert "--env-example .env.example" in scan["run"]
    assert "--env-example ../.env.example" in scan["run"]
    assert "continue-on-error" not in scan
    # The shards receive the scanned build only.
    assert names.index("Keep the build for the end-to-end shards") > names.index(
        "No secrets in the build"
    )


def test_the_rules_cover_the_providers_key_shapes() -> None:
    rules = RULES.read_text(encoding="utf-8")

    for shape in REQUIRED_SHAPES:
        assert shape in rules, shape
    scanner = SCANNER.read_text(encoding="utf-8")
    assert 'SCANNED_DIRECTORIES = ["static", "server"]' in scanner
    assert "process.exit(1)" in scanner and "process.exit(2)" in scanner


def test_the_proxy_drops_the_bypass_header_on_every_forwarded_request() -> None:
    helper = (WEB / "src" / "server" / "middlewareSubrequest.ts").read_text("utf-8")

    assert 'MIDDLEWARE_SUBREQUEST_HEADER = "x-middleware-subrequest"' in helper
    for module in ("src/proxy.ts", "src/server/hostedChatProxy.ts"):
        source = (WEB / module).read_text(encoding="utf-8")
        assert "forwardedRequestHeaders(request)" in source, module
        assert "new Headers(request.headers)" not in source, module
