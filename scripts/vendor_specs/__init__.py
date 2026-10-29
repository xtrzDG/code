"""
Vendored provider specifications for the contract tests.

`scripts/refresh_vendor_specs.py` downloads the machine-readable documents
the providers publish (OpenAPI, Google's discovery documents, the types of
vendor-generated SDKs), keeps only the schemas the platform exchanges with
them and writes them as self-contained JSON Schema files into
`tests/contracts/specs/` (tests/contracts/README.md).
"""
