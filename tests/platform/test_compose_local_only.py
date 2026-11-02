"""
docker-compose.yml is a local stack: its ports listen on this machine's
loopback only, its sample encryption key says it is local and production
refuses it, and the cabinet names its own local address (SITE_URL).
"""

import re

from app.adapters.security.secret_cipher_adapter import PUBLIC_ENCRYPTION_KEYS
from tests.platform.deployment_variables import compose_default, compose_environment
from tests.platform.environment_sources import read


def test_every_published_port_listens_on_loopback_only() -> None:
    compose: str = read("docker-compose.yml")
    published: list[str] = re.findall(
        r'^\s+- "([^"]+)"$', compose.split("\nvolumes:\n")[0], re.MULTILINE
    )
    ports: list[str] = [entry for entry in published if entry.count(":") >= 2]

    assert ports == [
        "127.0.0.1:${API_PORT:-8000}:8000",
        "127.0.0.1:${WEB_PORT:-3000}:3000",
    ]
    assert compose.count("ports:") == len(ports)


def test_the_sample_key_is_local_only_and_public() -> None:
    backend: dict[str, str] = compose_environment("x-backend: &backend")
    sample_key: str = compose_default(backend["ENCRYPTION_KEY"])

    assert "local" in sample_key and "only" in sample_key
    assert sample_key in PUBLIC_ENCRYPTION_KEYS
    assert "APP_ENV=production refuses to start with it" in read("docker-compose.yml")


def test_the_cabinet_names_its_own_local_address() -> None:
    backend: dict[str, str] = compose_environment("x-backend: &backend")
    web: dict[str, str] = compose_environment("  web:")

    assert web["SITE_URL"] == "http://localhost:${WEB_PORT:-3000}"
    assert web["SITE_URL"] == compose_default(backend["CABINET_BASE_URL"])
