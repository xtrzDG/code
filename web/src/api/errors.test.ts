import { describe, expect, it } from "vitest";

import { createTranslator } from "@/i18n/translate";
import { en } from "@/i18n/messages/en";
import { ru } from "@/i18n/messages/ru";

import {
  API_ERROR_CODES,
  ApiError,
  codeForStatus,
  describeError,
  errorMessageKey,
  isApiErrorCode,
  parseApiError,
  readApiError,
  toApiError,
  type BackendErrorBody,
  type BackendErrorCode,
} from "./errors";
import { unwrap } from "./result";

describe("parseApiError", () => {
  it("reads the backend's {error, message} body", () => {
    const error = parseApiError(429, { error: "rate_limited", message: "Wait 30 seconds." }, "req-1");
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(429);
    expect(error.code).toBe("rate_limited");
    expect(error.detail).toBe("Wait 30 seconds.");
    expect(error.requestId).toBe("req-1");
  });

  it("keeps the machine-readable reasons of a refusal", () => {
    const error = parseApiError(409, {
      error: "conflict",
      message: "The assistant cannot go live yet: Accept the agreement.",
      reasons: [
        { code: "dpa", message: "Accept the agreement.", details: ["2026-10-01"] },
        { code: "profile_gaps", details: ["no_address", 7] },
        { message: "no code" },
        "junk",
      ],
    });
    expect(error.reasons).toEqual([
      { code: "dpa", message: "Accept the agreement.", details: ["2026-10-01"] },
      { code: "profile_gaps", message: "", details: ["no_address"] },
    ]);
    expect(parseApiError(404, { error: "not_found", message: "Gone" }).reasons).toEqual([]);
  });

  it("falls back to the status for unknown error codes", () => {
    expect(parseApiError(409, { error: "slot_taken", message: "Taken" }).code).toBe("conflict");
  });

  it("reads the fields of an invalid request from its reasons", () => {
    const body: BackendErrorBody = {
      error: "validation_failed",
      message: "Invalid request: query.country_code: Field required",
      reasons: [{ code: "missing", message: "Field required", details: ["query.country_code"] }],
    };
    const error = parseApiError(422, body);
    expect(error.code).toBe("validation_failed");
    expect(error.detail).toBe("Invalid request: query.country_code: Field required");
    expect(error.reasons).toEqual([{ code: "missing", message: "Field required", details: ["query.country_code"] }]);
  });

  it("falls back to the status for bodies that are not an ErrorBody", () => {
    expect(parseApiError(422, { detail: [{ loc: ["query"], msg: "x" }] })).toMatchObject({
      code: "validation_failed",
      detail: null,
      reasons: [],
    });
    expect(parseApiError(404, { error: 7 }).code).toBe("not_found");
  });

  it("handles empty and non-JSON bodies", () => {
    expect(parseApiError(502, undefined).code).toBe("external_service_error");
    expect(parseApiError(500, "Internal Server Error").detail).toBe("Internal Server Error");
    expect(parseApiError(418, null).code).toBe("unknown_error");
  });
});

describe("error codes", () => {
  it("knows every backend code and the cabinet's own", () => {
    const backend: BackendErrorCode[] = [
      "not_found",
      "validation_failed",
      "conflict",
      "authentication_required",
      "access_denied",
      "rate_limited",
      "external_service_error",
      "internal_error",
    ];
    expect(API_ERROR_CODES).toEqual(expect.arrayContaining([...backend, "network_error", "backend_unavailable"]));
    expect(backend.every((code) => isApiErrorCode(code))).toBe(true);
    expect(isApiErrorCode("slot_taken")).toBe(false);
  });
});

describe("codeForStatus", () => {
  it.each([
    [401, "authentication_required"],
    [403, "access_denied"],
    [404, "not_found"],
    [422, "validation_failed"],
    [503, "backend_unavailable"],
    [500, "internal_error"],
  ] as const)("maps %i to %s", (status, code) => {
    expect(codeForStatus(status)).toBe(code);
  });
});

describe("toApiError", () => {
  it("turns fetch failures into network errors", () => {
    expect(toApiError(new TypeError("Failed to fetch")).code).toBe("network_error");
  });

  it("keeps ApiErrors as they are", () => {
    const error = new ApiError({ status: 404, code: "not_found" });
    expect(toApiError(error)).toBe(error);
  });
});

describe("readApiError", () => {
  it("reads status, body and request id of a Response", async () => {
    const response = new Response(JSON.stringify({ error: "access_denied", message: "Restricted" }), {
      status: 403,
      headers: { "content-type": "application/json", "x-request-id": "abc" },
    });
    const error = await readApiError(response);
    expect(error.code).toBe("access_denied");
    expect(error.requestId).toBe("abc");
  });
});

describe("friendly messages", () => {
  const tRu = createTranslator("ru", ru, en).t;
  const tEn = createTranslator("en", en).t;

  it("localizes by code", () => {
    const error = new ApiError({ status: 429, code: "rate_limited", detail: "Wait." });
    expect(describeError(error, tRu).title).toBe(ru.errors.codes.rate_limited);
    expect(describeError(error, tEn).title).toBe(en.errors.codes.rate_limited);
  });

  it("uses context-specific texts when given", () => {
    const error = new ApiError({ status: 403, code: "access_denied" });
    expect(errorMessageKey(error, { access_denied: "auth.errors.countryRestricted" })).toBe("auth.errors.countryRestricted");
    expect(describeError(error, tEn, { access_denied: "auth.errors.countryRestricted" }).title).toBe(
      en.auth.errors.countryRestricted,
    );
  });

  it("shows the backend detail only where it helps fix the input", () => {
    const validation = new ApiError({ status: 422, code: "validation_failed", detail: "hours overlap" });
    const denied = new ApiError({ status: 403, code: "access_denied", detail: "internal reason" });
    expect(describeError(validation, tEn).detail).toBe("hours overlap");
    expect(describeError(denied, tEn).detail).toBeNull();
  });

  it("offers the request id for server errors", () => {
    const error = new ApiError({ status: 500, code: "internal_error", requestId: "req-9" });
    expect(describeError(error, tEn).requestId).toBe("req-9");
  });
});

describe("unwrap", () => {
  const response = (status: number, headers: Record<string, string> = {}) => new Response(null, { status, headers });

  it("returns the data of a successful call", async () => {
    await expect(unwrap(Promise.resolve({ data: { id: 1 }, response: response(200) }))).resolves.toEqual({ id: 1 });
  });

  it("throws ApiError for an error answer", async () => {
    const failing = unwrap(
      Promise.resolve({
        error: { error: "not_found", message: "Business was not found." },
        response: response(404, { "x-request-id": "r1" }),
      }),
    );
    await expect(failing).rejects.toMatchObject({ code: "not_found", status: 404, requestId: "r1" });
  });

  it("throws for a failed status even without a body", async () => {
    await expect(unwrap(Promise.resolve({ response: response(401) }))).rejects.toMatchObject({
      code: "authentication_required",
    });
  });

  it("throws network_error when fetch rejects", async () => {
    await expect(unwrap(Promise.reject(new TypeError("offline")))).rejects.toMatchObject({ code: "network_error" });
  });
});
