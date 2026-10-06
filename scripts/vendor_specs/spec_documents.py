"""Reading the vendor documents: downloaded, or from a cache directory."""

import importlib.metadata
import json
from pathlib import Path
from typing import cast
from urllib.parse import urlparse

import httpx
import yaml

from scripts.vendor_specs.spec_model import DocumentFormat, JsonObject, VendorSpec

DOWNLOAD_TIMEOUT_SECONDS: float = 120.0
YAML_SUFFIXES: tuple[str, ...] = (".yaml", ".yml")


class VendorDocumentError(ValueError):
    """A vendor document that could not be fetched or read."""


def cache_name(spec: VendorSpec) -> str:
    """The file a document is kept under in a cache directory."""

    suffix: str = Path(urlparse(spec.source_url).path).suffix or ".json"
    return f"{spec.provider}{suffix}"


def load_document(spec: VendorSpec, cache_directory: Path | None) -> JsonObject:
    """
    The vendor document of a spec. With a cache directory, a document
    already there is read instead of downloaded, and a download is kept
    there (the nightly workflow keeps them as an artifact).
    """

    if spec.document_format is DocumentFormat.PYTHON_SDK:
        return {}

    if cache_directory is None:
        return parse_document(download(spec.source_url), spec.source_url)

    cached: Path = cache_directory / cache_name(spec)
    try:
        text: str = cached.read_text(encoding="utf-8")
    except FileNotFoundError:
        text = download(spec.source_url)
        cache_directory.mkdir(parents=True, exist_ok=True)
        cached.write_text(text, encoding="utf-8")

    return parse_document(text, spec.source_url)


def download(url: str) -> str:
    try:
        response: httpx.Response = httpx.get(
            url, timeout=DOWNLOAD_TIMEOUT_SECONDS, follow_redirects=True
        )
        response.raise_for_status()
    except httpx.HTTPError as error:
        raise VendorDocumentError(f"{url}: {type(error).__name__}") from error

    return response.text


def parse_document(text: str, url: str) -> JsonObject:
    parsed: object = (
        yaml.safe_load(text)
        if urlparse(url).path.endswith(YAML_SUFFIXES)
        else json.loads(text)
    )
    if not isinstance(parsed, dict):
        raise VendorDocumentError(f"{url} is not a JSON object.")

    return cast(JsonObject, parsed)


def document_version(spec: VendorSpec, document: JsonObject) -> str:
    """The vendor's version label of the document (or of the SDK)."""

    if spec.document_format is DocumentFormat.PYTHON_SDK:
        package: str = spec.roots[0].selector.split(":")[1].split(".")[0]
        return f"{package} {importlib.metadata.version(package)}"

    if spec.document_format is DocumentFormat.GOOGLE_DISCOVERY:
        return str(document.get("version", "unknown"))

    info: object = document.get("info")
    version: object = (
        cast(JsonObject, info).get("version") if isinstance(info, dict) else None
    )
    return str(version) if version not in (None, "") else "unversioned"
