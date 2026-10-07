/**
 * Errors of the backend API and of the cabinet's own route handlers.
 *
 * Every failure of the backend is an `ErrorBody` ({"error", "message",
 * "reasons"?}, app/gateways/http/error_responses.py), also the framework's
 * own refusals (a missing parameter, an unknown route); the types below are
 * read from the generated API description, so a new backend code fails the
 * type check until it has a text. Every failure ends up as an ApiError with
 * a stable `code`; the UI shows the localized text of the code
 * (errors.codes.*), not the English backend message. Refusals may carry
 * `reasons` ({code, message, details}: the failed go-live checks of a
 * publish, the fields of an invalid request); screens map those codes to
 * their own texts.
 */

import type { MessageKey, MessageValues, PluralKey, Translator } from "@/i18n/translate";

import type { components } from "./schema";

/** The body of every failed backend request. */
export type BackendErrorBody = components["schemas"]["ErrorBody"];
/** The broad codes the backend answers with (`ErrorBody.error`). */
export type BackendErrorCode = components["schemas"]["ApiErrorCode"];

/** Every backend code, checked against the API description in both directions. */
const BACKEND_ERROR_CODE_SET: Readonly<Record<BackendErrorCode, true>> = {
  not_found: true,
  validation_failed: true,
  conflict: true,
  authentication_required: true,
  access_denied: true,
  rate_limited: true,
  payload_too_large: true,
  external_service_error: true,
  internal_error: true,
};

/** Codes of the cabinet's own route handlers and of the browser. */
const CABINET_ERROR_CODES = ["backend_unavailable", "network_error", "forbidden_origin", "unknown_error"] as const;

export const API_ERROR_CODES = [
  ...(Object.keys(BACKEND_ERROR_CODE_SET) as BackendErrorCode[]),
  ...CABINET_ERROR_CODES,
] as const;

export type ApiErrorCode = BackendErrorCode | (typeof CABINET_ERROR_CODES)[number];

/**
 * One machine-readable reason of a refusal (the backend's `ErrorReason`,
 * with `details` always present): e.g. "dpa", or "missing" with the field's
 * location ("query.country_code") for an invalid request.
 */
export type ApiErrorReason = Required<components["schemas"]["ErrorReason"]>;

export class ApiError extends Error {
  readonly status: number;
  readonly code: ApiErrorCode;
  /** The backend's own (English, technical) message, if any. */
  readonly detail: string | null;
  /** X-Request-ID of the failed request, for support. */
  readonly requestId: string | null;
  /** Machine-readable reasons, when the backend gave any. */
  readonly reasons: readonly ApiErrorReason[];

  constructor(init: {
    status: number;
    code: ApiErrorCode;
    detail?: string | null;
    requestId?: string | null;
    reasons?: readonly ApiErrorReason[];
  }) {
    super(init.detail ?? init.code);
    this.name = "ApiError";
    this.status = init.status;
    this.code = init.code;
    this.detail = init.detail ?? null;
    this.requestId = init.requestId ?? null;
    this.reasons = init.reasons ?? [];
  }
}

export function isApiError(value: unknown): value is ApiError {
  return value instanceof ApiError;
}

export function isApiErrorCode(value: unknown): value is ApiErrorCode {
  return typeof value === "string" && (API_ERROR_CODES as readonly string[]).includes(value);
}

/** The code for an HTTP status when the body does not name one. */
export function codeForStatus(status: number): ApiErrorCode {
  switch (status) {
    case 400:
    case 422:
      return "validation_failed";
    case 401:
      return "authentication_required";
    case 403:
      return "access_denied";
    case 404:
      return "not_found";
    case 409:
      return "conflict";
    case 413:
      return "payload_too_large";
    case 429:
      return "rate_limited";
    case 502:
    case 504:
      return "external_service_error";
    case 503:
      return "backend_unavailable";
    default:
      return status >= 500 ? "internal_error" : "unknown_error";
  }
}

/** The well-formed entries of a body's `reasons` list (others are skipped). */
function parseErrorReasons(value: unknown): ApiErrorReason[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.flatMap((item: unknown): ApiErrorReason[] => {
    if (!item || typeof item !== "object") {
      return [];
    }
    const { code, message, details } = item as { code?: unknown; message?: unknown; details?: unknown };
    if (typeof code !== "string") {
      return [];
    }
    return [
      {
        code,
        message: typeof message === "string" ? message : "",
        details: Array.isArray(details) ? details.filter((detail): detail is string => typeof detail === "string") : [],
      },
    ];
  });
}

/** Whether a parsed body looks like an ErrorBody (its code is a string). */
function isErrorBodyShaped(body: unknown): body is { error: string; message?: unknown; reasons?: unknown } {
  return body !== null && typeof body === "object" && typeof (body as { error?: unknown }).error === "string";
}

/** An ApiError from a failed response's status and parsed JSON body. */
export function parseApiError(
  status: number,
  body: unknown,
  requestId: string | null = null,
): ApiError {
  if (isErrorBodyShaped(body)) {
    return new ApiError({
      status,
      code: isApiErrorCode(body.error) ? body.error : codeForStatus(status),
      detail: typeof body.message === "string" ? body.message : null,
      requestId,
      reasons: parseErrorReasons(body.reasons),
    });
  }

  return new ApiError({
    status,
    code: codeForStatus(status),
    detail: typeof body === "string" && body.trim() !== "" ? body.trim() : null,
    requestId,
  });
}

/** Any thrown value as an ApiError (fetch failures become `network_error`). */
export function toApiError(error: unknown): ApiError {
  if (isApiError(error)) {
    return error;
  }
  if (error instanceof TypeError || (error instanceof DOMException && error.name === "AbortError")) {
    return new ApiError({ status: 0, code: "network_error", detail: error.message });
  }
  return new ApiError({
    status: 0,
    code: "unknown_error",
    detail: error instanceof Error ? error.message : null,
  });
}

/** Read a failed fetch Response into an ApiError. */
export async function readApiError(response: Response): Promise<ApiError> {
  const requestId = response.headers.get("x-request-id");
  const text = await response.text().catch(() => "");
  let body: unknown = text;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    // Not JSON: keep the text.
  }
  return parseApiError(response.status, body, requestId);
}

const ERROR_MESSAGE_KEYS: Record<ApiErrorCode, MessageKey> = {
  not_found: "errors.codes.not_found",
  validation_failed: "errors.codes.validation_failed",
  conflict: "errors.codes.conflict",
  authentication_required: "errors.codes.authentication_required",
  access_denied: "errors.codes.access_denied",
  rate_limited: "errors.codes.rate_limited",
  payload_too_large: "errors.codes.payload_too_large",
  external_service_error: "errors.codes.external_service_error",
  internal_error: "errors.codes.internal_error",
  backend_unavailable: "errors.codes.backend_unavailable",
  network_error: "errors.codes.network_error",
  forbidden_origin: "errors.codes.forbidden_origin",
  unknown_error: "errors.codes.unknown_error",
};

/** Context-specific texts, e.g. `{ access_denied: "auth.errors.countryRestricted" }`. */
export type ErrorMessageOverrides = Partial<Record<ApiErrorCode, MessageKey>>;

/**
 * The text of one refusal reason: a message key and values from its
 * details, or plural forms and the count that picks one ("up to 1 webhook",
 * "up to 10 webhooks").
 */
type ReasonText =
  | { key: MessageKey; values?: MessageValues }
  | { pluralKey: PluralKey; count: number; values?: MessageValues };

type ReasonMessage = (reason: ApiErrorReason) => ReasonText;

/**
 * Localized texts for refusal reason codes, e.g. a booking refused because
 * the business is closed that day. A matching reason replaces the generic
 * title and the backend's English detail.
 */
export type ReasonMessages = Readonly<Record<string, ReasonMessage>>;

/** Codes whose backend message helps the user fix the input (shown as a detail line). */
const CODES_WITH_USEFUL_DETAIL: ReadonlySet<ApiErrorCode> = new Set(["validation_failed", "conflict"]);

export function errorMessageKey(error: ApiError, overrides?: ErrorMessageOverrides): MessageKey {
  return overrides?.[error.code] ?? ERROR_MESSAGE_KEYS[error.code];
}

export interface ErrorDescription {
  title: string;
  detail: string | null;
  requestId: string | null;
}

type Translate = (key: MessageKey, values?: MessageValues) => string;

/** Localized title (and, where useful, the backend detail) for an error toast. */
export function describeError(error: unknown, t: Translate, overrides?: ErrorMessageOverrides): ErrorDescription;
/** The same with refusal reasons in the user's language: they may count, so they need the whole translator. */
export function describeError(
  error: unknown,
  texts: Pick<Translator, "t" | "tp">,
  overrides?: ErrorMessageOverrides,
  reasonMessages?: ReasonMessages,
): ErrorDescription;
export function describeError(
  error: unknown,
  texts: Translate | Pick<Translator, "t" | "tp">,
  overrides?: ErrorMessageOverrides,
  reasonMessages?: ReasonMessages,
): ErrorDescription {
  const t = typeof texts === "function" ? texts : texts.t;
  const apiError = toApiError(error);
  const known = reasonMessages ? apiError.reasons.find((reason) => Object.hasOwn(reasonMessages, reason.code)) : undefined;
  if (known && reasonMessages && typeof texts !== "function") {
    const message = reasonMessages[known.code]?.(known);
    if (message) {
      const title = "pluralKey" in message ? texts.tp(message.pluralKey, message.count, message.values) : t(message.key, message.values);
      return { title, detail: null, requestId: null };
    }
  }
  const overridden = overrides?.[apiError.code] !== undefined;
  return {
    title: t(errorMessageKey(apiError, overrides)),
    detail: !overridden && CODES_WITH_USEFUL_DETAIL.has(apiError.code) ? apiError.detail : null,
    requestId: apiError.code === "internal_error" ? apiError.requestId : null,
  };
}
