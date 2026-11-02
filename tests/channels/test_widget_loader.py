"""
The widget's loader (WEB-02, PCI SAQ A script integrity): embed codes name
an immutable, versioned file and pin it with its integrity hash, while
/widget.js keeps serving existing embeds and carries every deploy.
"""

import base64
import hashlib

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.gateways.http.cabinet_cors_middleware import is_self_cors_path
from app.gateways.http.widget_script_routes import build_widget_script_router
from app.schemas.constants.environment import DeploymentEnvironment
from app.schemas.typings.widget_embedding.constrained_strings import (
    WidgetLoaderIntegrity,
    WidgetLoaderUrl,
)
from app.utilities.channels.channel_endpoints import WIDGET_SCRIPT_PATH
from app.utilities.channels.widget_loader import (
    LOADER_SOURCE_FILE,
    current_widget_loader,
    describe_loader,
    published_widget_loaders,
)

# The loader every embed code pasted so far names. Changing the loader's
# source changes this address: the old file must then stay served (add it
# to published_widget_loaders beside the new one), or those websites lose
# the chat.
FIRST_PUBLISHED_PATH: str = "/widget/v/8cc8877aaa264465.js"


def client(environment: DeploymentEnvironment) -> TestClient:
    application = FastAPI()
    application.include_router(build_widget_script_router(environment))
    return TestClient(application)


def test_the_loader_is_served_immutable_to_any_site_in_production() -> None:
    loader = current_widget_loader()

    response = client(DeploymentEnvironment.PRODUCTION).get(
        loader.path, headers={"Origin": "https://salon.example"}
    )

    assert response.status_code == 200
    assert response.content == LOADER_SOURCE_FILE.read_bytes()
    assert response.headers["content-type"] == "text/javascript; charset=utf-8"
    assert response.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert response.headers["access-control-allow-origin"] == "*"
    assert response.headers["cross-origin-resource-policy"] == "cross-origin"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert is_self_cors_path(loader.path)


def test_the_integrity_hash_is_the_one_a_browser_computes() -> None:
    loader = current_widget_loader()
    served: bytes = client(DeploymentEnvironment.DEVELOPMENT).get(loader.path).content

    expected: str = (
        "sha384-" + base64.b64encode(hashlib.sha384(served).digest()).decode()
    )
    assert loader.integrity == expected
    assert WidgetLoaderIntegrity(loader.integrity) == expected
    assert WidgetLoaderUrl(f"https://api.example.com{loader.path}")


def test_the_address_names_the_content() -> None:
    loader = describe_loader(b"console.log(1);\n")

    assert loader.path == (
        "/widget/v/" + hashlib.sha256(b"console.log(1);\n").hexdigest()[:16] + ".js"
    )
    assert loader.path != current_widget_loader().path


def test_every_published_loader_stays_served() -> None:
    application = client(DeploymentEnvironment.PRODUCTION)
    loaders = published_widget_loaders()

    assert FIRST_PUBLISHED_PATH in loaders
    for path, loader in loaders.items():
        assert describe_loader(loader.body) == loader
        assert application.get(path).content == loader.body


def test_other_versions_are_not_found_and_widget_js_keeps_working() -> None:
    application = client(DeploymentEnvironment.PRODUCTION)

    assert application.get("/widget/v/0000000000000000.js").status_code == 404
    assert application.get(WIDGET_SCRIPT_PATH).status_code == 200


def test_the_loader_only_adds_the_widget_with_the_tag_settings() -> None:
    source: str = LOADER_SOURCE_FILE.read_text(encoding="utf-8")

    # No markup, no other address, no storage: the tag's data-* settings
    # are copied onto one new script element for /widget.js.
    assert 'var WIDGET_FILE = "/widget.js";' in source
    assert 'attribute.name.indexOf("data-") === 0' in source
    assert "createScriptURL" in source
    for forbidden in ("innerHTML", "document.write", "eval(", "Storage", "http:"):
        assert forbidden not in source
