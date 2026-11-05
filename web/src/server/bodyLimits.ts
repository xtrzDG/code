/**
 * Request body limits of the BFF, the same as the API's
 * (app/gateways/http/middleware/body_size_limit_middleware.py): a body over
 * the limit is refused with 413 `payload_too_large` before it is read
 * (Content-Length) or as soon as it grows over the limit while streaming,
 * so the cabinet's server never buffers or forwards more.
 */

const KIBIBYTE = 1024;
const MEBIBYTE = 1024 * KIBIBYTE;
/** JSON of a cabinet form or a sign-in. */
export const DEFAULT_BODY_LIMIT_BYTES = 256 * KIBIBYTE;
/** A 15 MB menu photo or PDF as base64 in JSON. */
export const MENU_IMPORT_BODY_LIMIT_BYTES = 21 * MEBIBYTE;
const MENU_IMPORT_PATH = /^\/v1\/businesses\/[^/]+\/knowledge\/import$/;

/** The limit of a request to an API path ("/v1/..."). */
export function bodyLimitFor(backendPath: string): number {
  return MENU_IMPORT_PATH.test(backendPath) ? MENU_IMPORT_BODY_LIMIT_BYTES : DEFAULT_BODY_LIMIT_BYTES;
}

/** True when the declared Content-Length is over the limit. */
export function isDeclaredTooLarge(headers: Headers, limit: number): boolean {
  const declared = headers.get("content-length");
  return declared !== null && /^\d+$/.test(declared) && Number(declared) > limit;
}

export class BodyTooLargeError extends Error {
  constructor(readonly limit: number) {
    super(`The request body is larger than the ${Math.floor(limit / KIBIBYTE)} KB allowed here.`);
    this.name = "BodyTooLargeError";
  }
}

/**
 * The body stream, cut off with BodyTooLargeError once more than `limit`
 * bytes went through (a chunked or understated body).
 */
export function limitBodyStream(
  body: ReadableStream<Uint8Array>,
  limit: number,
): ReadableStream<Uint8Array> {
  let received = 0;
  return body.pipeThrough(
    new TransformStream<Uint8Array, Uint8Array>({
      transform(chunk, controller) {
        received += chunk.byteLength;
        if (received > limit) {
          controller.error(new BodyTooLargeError(limit));
          return;
        }
        controller.enqueue(chunk);
      },
    }),
  );
}

/** The whole body as text, refused over the limit (small JSON bodies). */
export async function readLimitedText(request: Request, limit: number): Promise<string> {
  if (isDeclaredTooLarge(request.headers, limit)) {
    throw new BodyTooLargeError(limit);
  }
  if (!request.body) {
    return "";
  }
  return new Response(limitBodyStream(request.body, limit)).text();
}

export function payloadTooLargeMessage(limit: number): string {
  return new BodyTooLargeError(limit).message;
}
