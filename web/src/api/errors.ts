/**
 * Errors of the backend API and of the cabinet's own route handlers.
 *
 * The backend answers errors as {"error": "<code>", "message": "<English text>"}
 * (FastAPI's own validation errors as {"detail": [...]}). Every failure ends
 * up as an ApiError with a stable `code`; the UI shows the localized text of
 * the code (errors.codes.*), not the English backend message. Some refusals
 * also carry `reasons` ({code, message, details}: the failed go-live checks
 * of a publish, why a menu link could not be read); screens map those codes
 * to their own texts.
 */

import type { MessageKey, MessageValues } from "@/i18n/translate";

export const API_ERROR_CODES = [
  // Backend (app/gateways/http/error_responses.py)
  "not_found",
  "validation_failed",
  "conflict",
  "authentication_required",
  "access_denied",
  "rate_limited",
  "external_service_error",
  "internal_error",
  // Cabinet route handlers and the browser
  "backend_unavailable",
  "network_error",
  "forbidden_origin",
  "unknown_error",
] as const;

export type ApiErrorCode = (typeof API_ERROR_CODES)[number];

/** One machine-readable reason of a refusal (the backend's `reasons[]`). */
export interface ApiErrorReason {
  /** Stable code, e.g. "dpa" or "menu_link_unreachable". */
  code: string;
  /** The backend's English explanation (a fallback for unknown codes). */
  message: string;
  /** Values that qualify it: gap kinds, statuses, "http_status:404". */
  details: string[];
}

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

function describeValidationDetail(detail: unknown): string | null {
  if (typeof detail === "string") {
    return detail;
  }
  if (!Array.isArray(detail)) {
    return null;
  }

  const parts = detail
    .map((item: unknown) => {
      if (!item || typeof item !== "object") {
        return null;
      }
      const { loc, msg } = item as { loc?: unknown; msg?: unknown };
      const location = Array.isArray(loc) ? loc.join(".") : "";
      return typeof msg === "string" ? (location ? `${location}: ${msg}` : msg) : null;
    })
    .filter((part): part is string => part !== null);
  return parts.length > 0 ? parts.join("; ") : null;
}

/** The well-formed entries of a body's `reasons` list (others are skipped). */
export function parseErrorReasons(value: unknown): ApiErrorReason[] {
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

/** An ApiError from a failed response's status and parsed JSON body. */
export function parseApiError(
  status: number,
  body: unknown,
  requestId: string | null = null,
): ApiError {
  if (body && typeof body === "object") {
    const { error, message, detail, reasons } = body as {
      error?: unknown;
      message?: unknown;
      detail?: unknown;
      reasons?: unknown;
    };
    if (typeof error === "string") {
      return new ApiError({
        status,
        code: isApiErrorCode(error) ? error : codeForStatus(status),
        detail: typeof message === "string" ? message : null,
        requestId,
        reasons: parseErrorReasons(reasons),
      });
    }
    if (detail !== undefined) {
      return new ApiError({
        status,
        code: codeForStatus(status),
        detail: describeValidationDetail(detail),
        requestId,
      });
    }
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
  external_service_error: "errors.codes.external_service_error",
  internal_error: "errors.codes.internal_error",
  backend_unavailable: "errors.codes.backend_unavailable",
  network_error: "errors.codes.network_error",
  forbidden_origin: "errors.codes.forbidden_origin",
  unknown_error: "errors.codes.unknown_error",
};

/** Context-specific texts, e.g. `{ access_denied: "auth.errors.countryRestricted" }`. */
export type ErrorMessageOverrides = Partial<Record<ApiErrorCode, MessageKey>>;

/** The text of one refusal reason: a message key and values from its details. */
export type ReasonMessage = (reason: ApiErrorReason) => { key: MessageKey; values?: MessageValues };

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

/** Localized title (and, where useful, the backend detail) for an error toast. */
export function describeError(
  error: unknown,
  t: (key: MessageKey, values?: MessageValues) => string,
  overrides?: ErrorMessageOverrides,
  reasonMessages?: ReasonMessages,
): ErrorDescription {
  const apiError = toApiError(error);
  const known = reasonMessages ? apiError.reasons.find((reason) => Object.hasOwn(reasonMessages, reason.code)) : undefined;
  if (known && reasonMessages) {
    const message = reasonMessages[known.code]?.(known);
    if (message) {
      return { title: t(message.key, message.values), detail: null, requestId: null };
    }
  }
  const overridden = overrides?.[apiError.code] !== undefined;
  return {
    title: t(errorMessageKey(apiError, overrides)),
    detail: !overridden && CODES_WITH_USEFUL_DETAIL.has(apiError.code) ? apiError.detail : null,
    requestId: apiError.code === "internal_error" ? apiError.requestId : null,
  };
}
