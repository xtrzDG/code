"""Render and Docker Compose set exactly the variables a deployment needs."""

import re

from app.adapters.security.secret_cipher_adapter import (
    MIN_DERIVED_SECRET_LENGTH,
    PUBLIC_ENCRYPTION_KEYS,
)
from tests.platform.deployment_variables import (
    COMPOSE_VARIABLES,
    DEPLOYMENT_VARIABLES,
    RENDER_OPTIONAL_VARIABLES,
    REQUIRED_BACKEND_VARIABLES,
    REQUIRED_CABINET_VARIABLES,
    compose_default,
    compose_environment,
    render_services,
)
from tests.platform.environment_sources import (
    backend_variables,
    cabinet_variables,
    env_file_values,
    read,
)


def test_deployment_files_set_only_known_variables() -> None:
    known: set[str] = backend_variables() | DEPLOYMENT_VARIABLES | cabinet_variables()
    compose: str = read("docker-compose.yml")
    compose_variables: set[str] = set(compose_environment("x-backend: &backend"))
    compose_variables |= set(compose_environment("  web:"))
    interpolated: set[str] = set(re.findall(r"\$\{([A-Z][A-Z0-9_]*)", compose))

    for service, variables in render_services().items():
        assert variables - known == set(), service
    assert compose_variables - known == set()
    assert interpolated - known - COMPOSE_VARIABLES == set()


def test_render_sets_what_a_deployment_needs() -> None:
    services: dict[str, set[str]] = render_services()
    api: set[str] = services["workshop-api"]
    without_default: set[str] = {
        name
        for name, value in env_file_values(".env.example", False).items()
        if value == ""
    }

    assert api >= REQUIRED_BACKEND_VARIABLES | {"PORT"}
    assert without_default - RENDER_OPTIONAL_VARIABLES - api == set()
    # The worker runs the same code with the same settings.
    assert services["workshop-worker"] == api - {"PORT"}
    assert services["workshop-cabinet"] >= REQUIRED_CABINET_VARIABLES | {
        "TRUSTED_PROXY_HOPS"
    }


def test_the_render_worker_copies_the_api_values() -> None:
    worker: str = read("render.yaml").split("    name: workshop-worker\n", 1)[1]
    worker = worker.split("\n  - type: ", 1)[0]

    copies: list[tuple[str, str, str]] = re.findall(
        r"- key: ([A-Z0-9_]+)\n\s+fromService:\n\s+type: web\n\s+name: (\S+)\n"
        r"\s+envVarKey: ([A-Z0-9_]+)",
        worker,
    )

    assert len(copies) == worker.count("fromService:") > 0
    for key, service, source_key in copies:
        assert (service, source_key) == ("workshop-api", key)


def test_compose_sets_what_a_local_run_needs() -> None:
    backend: dict[str, str] = compose_environment("x-backend: &backend")
    web: dict[str, str] = compose_environment("  web:")

    assert set(backend) >= REQUIRED_BACKEND_VARIABLES
    assert set(web) >= REQUIRED_CABINET_VARIABLES
    # API and worker share one key by default, long enough to use as is;
    # production refuses it, since it is printed here.
    assert len(compose_default(backend["ENCRYPTION_KEY"])) >= MIN_DERIVED_SECRET_LENGTH
    assert compose_default(backend["ENCRYPTION_KEY"]) in PUBLIC_ENCRYPTION_KEYS
    # The cabinet's address is also its origin; its server reaches the API
    # inside the Compose network.
    assert compose_default(backend["CABINET_BASE_URL"]) == compose_default(
        backend["CORS_ALLOWED_ORIGINS"]
    )
    # Addresses follow the published ports, so changing API_PORT or WEB_PORT
    # in .env (docs/LAUNCH.md) keeps the widget code, its preview and the
    # cabinet's address reachable.
    assert compose_default(backend["APP_BASE_URL"]) == (
        "http://localhost:${API_PORT:-8000}"
    )
    assert compose_default(backend["CABINET_BASE_URL"]) == (
        "http://localhost:${WEB_PORT:-3000}"
    )
    assert web["BACKEND_URL"] == "http://api:8000"
