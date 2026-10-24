# 0003. The cabinet talks to the API only through its own server (BFF)

- Status: Accepted
- Date: 2026-10-02

## Context

The owner cabinet (`web/`, Next.js) shows customers' personal data. A
bearer token readable by browser JavaScript can be stolen by any script
injection, and calling the API directly from the browser would also expose
the API's address and require CORS for every cabinet route.

## Decision

- The browser calls only the cabinet's own routes. `web/src/app/api/backend/*`
  relays requests to the Python API (`BACKEND_URL`, server side only) and
  adds the session token from an httpOnly, `SameSite=Lax`, `Secure` cookie
  that scripts cannot read (`web/src/server/`).
- Browser code uses one typed client (`@/api/client`, generated types in
  `src/api/schema.d.ts` from `web/openapi.json`) and never sees the token.
- The API keeps its own authorization on every route; the BFF adds no
  business rules.

## Consequences

- A cross-site script cannot exfiltrate the session token, and the API can
  stay on an internal address.
- Every cabinet request takes one extra hop through the Next.js server;
  relays stream bodies (recordings, exports) instead of buffering them.
- The OpenAPI description is a contract between two deployables: CI checks
  that the generated client is current and that `/v1` changes stay
  additive (`docs/api-versioning.md`).
