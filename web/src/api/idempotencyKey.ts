/**
 * One Idempotency-Key per user action (docs/api-versioning.md): every POST
 * the cabinet sends gets a fresh key, and a retry of that request (the copy
 * stepUp.ts sends again after a confirmation) carries the same key, so the
 * API answers the retry with the first answer instead of creating a second
 * booking, message, checkout or assistant. The API honours the key on its
 * creating operations and ignores it elsewhere. Register it before the
 * retry middleware, so the copy it keeps already has the key.
 */

import type { Middleware } from "openapi-fetch";

export const IDEMPOTENCY_KEY_HEADER = "Idempotency-Key";

export const idempotencyKeys: Middleware = {
  onRequest({ request }) {
    if (request.method === "POST" && !request.headers.has(IDEMPOTENCY_KEY_HEADER)) {
      request.headers.set(IDEMPOTENCY_KEY_HEADER, crypto.randomUUID());
    }
    return request;
  },
};
