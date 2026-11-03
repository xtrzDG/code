"""
Every provider client is built by `build_provider_http_client` (OWASP
API10): no code under `app/` builds an httpx client itself, turns TLS
checks off or follows redirects, every factory call names its timeout and
its response cap, every module that takes a test transport builds its
client through the factory, and the model SDKs (OpenAI, Anthropic, which
build their own httpx2 clients) name their timeouts and retries.
"""

import ast
from pathlib import Path

import pytest

ROOT: Path = Path(__file__).resolve().parents[2]
APP: Path = ROOT / "app"
FACTORY_MODULE: str = "app/clients/http/provider_http_client.py"
FACTORY_NAME: str = "build_provider_http_client"
SDK_CONSTRUCTORS: frozenset[str] = frozenset({"OpenAI", "Anthropic"})


def parsed_modules() -> list[tuple[str, ast.Module]]:
    return [
        (str(path.relative_to(ROOT)), ast.parse(path.read_text(encoding="utf-8")))
        for path in sorted(APP.rglob("*.py"))
    ]


MODULES: list[tuple[str, ast.Module]] = parsed_modules()


def calls(tree: ast.Module) -> list[ast.Call]:
    return [node for node in ast.walk(tree) if isinstance(node, ast.Call)]


def callee(call: ast.Call) -> str:
    function = call.func
    if isinstance(function, ast.Attribute):
        prefix: str = function.value.id if isinstance(function.value, ast.Name) else ""
        return f"{prefix}.{function.attr}"

    return function.id if isinstance(function, ast.Name) else ""


def keyword(call: ast.Call, name: str) -> ast.expr | None:
    return next((item.value for item in call.keywords if item.arg == name), None)


def takes_a_test_transport(tree: ast.Module) -> bool:
    return any(
        isinstance(node, ast.arg)
        and node.arg == "transport"
        and node.annotation is not None
        and "httpx.BaseTransport" in ast.unparse(node.annotation)
        for node in ast.walk(tree)
    )


def hands_its_transport_on(call: ast.Call) -> bool:
    given: list[ast.expr] = [*call.args, *(item.value for item in call.keywords)]
    return any(
        isinstance(value, ast.Name) and value.id == "transport" for value in given
    )


def test_no_module_builds_an_httpx_client_itself() -> None:
    builders = [
        f"{module}:{call.lineno}"
        for module, tree in MODULES
        for call in calls(tree)
        if callee(call) in {"httpx.Client", "httpx.AsyncClient"}
        and module != FACTORY_MODULE
    ]

    assert builders == []


def test_no_module_sends_a_request_without_a_client() -> None:
    """`httpx.get(...)` and friends build a client of their own each call."""

    shortcuts: frozenset[str] = frozenset(
        f"httpx.{name}"
        for name in (
            "get",
            "post",
            "put",
            "patch",
            "delete",
            "head",
            "request",
            "stream",
        )
    )
    direct = [
        f"{module}:{call.lineno}"
        for module, tree in MODULES
        for call in calls(tree)
        if callee(call) in shortcuts
    ]

    assert direct == []


def test_nothing_turns_tls_checks_off_or_follows_redirects() -> None:
    unsafe: list[str] = []
    for module, tree in MODULES:
        for call in calls(tree):
            verify = keyword(call, "verify")
            follow = keyword(call, "follow_redirects")
            if isinstance(verify, ast.Constant) and verify.value is False:
                unsafe.append(f"{module}:{call.lineno} verify=False")
            if isinstance(follow, ast.Constant) and follow.value is True:
                unsafe.append(f"{module}:{call.lineno} follow_redirects=True")

    assert unsafe == []


def test_every_factory_call_names_its_timeout_and_its_cap() -> None:
    sites: list[tuple[str, int, bool]] = [
        (
            module,
            call.lineno,
            keyword(call, "timeout") is not None
            and keyword(call, "max_response_bytes") is not None,
        )
        for module, tree in MODULES
        for call in calls(tree)
        if callee(call).endswith(FACTORY_NAME) and module != FACTORY_MODULE
    ]

    assert len(sites) >= 23
    assert [site for site in sites if not site[2]] == []


def test_every_client_that_takes_a_transport_uses_the_factory() -> None:
    clients: list[str] = [
        module
        for module, tree in MODULES
        if module.startswith("app/clients/")
        and module != FACTORY_MODULE
        and takes_a_test_transport(tree)
    ]
    # A client either builds through the factory or hands its transport to
    # one that does (GoogleCalendarClient -> GoogleHttp).
    without_factory: list[str] = [
        module
        for module in clients
        if not any(
            callee(call).endswith(FACTORY_NAME) or hands_its_transport_on(call)
            for call in calls(dict(MODULES)[module])
        )
    ]

    assert len(clients) >= 20
    assert without_factory == []


@pytest.mark.parametrize(
    "module",
    sorted(
        module
        for module, tree in MODULES
        if any(callee(call).split(".")[-1] in SDK_CONSTRUCTORS for call in calls(tree))
    ),
)
def test_sdk_clients_set_their_timeout_and_retries(module: str) -> None:
    """
    The OpenAI and Anthropic SDKs build their own clients (over httpx2,
    which verifies certificates); each construction names its timeout and
    its retries, never a client of its own with other rules.
    """

    tree = dict(MODULES)[module]
    for call in calls(tree):
        if callee(call).split(".")[-1] not in SDK_CONSTRUCTORS:
            continue

        assert keyword(call, "timeout") is not None, f"{module}:{call.lineno}"
        assert keyword(call, "max_retries") is not None, f"{module}:{call.lineno}"
        assert keyword(call, "http_client") is None, f"{module}:{call.lineno}"
