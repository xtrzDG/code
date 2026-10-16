import { describe, expect, it, vi } from "vitest";

import { sourceMapUploadOptions, warnUploadFailed } from "./sourceMaps";

const TOKEN = "test-token-0000"; // gitleaks:allow

describe("sourceMapUploadOptions", () => {
  it("leaves a build without SENTRY_AUTH_TOKEN alone", () => {
    expect(sourceMapUploadOptions({})).toBeNull();
    expect(sourceMapUploadOptions({ SENTRY_AUTH_TOKEN: "  ", SENTRY_ORG: "workshop" })).toBeNull();
  });

  it("uploads for the commit's release and deletes the maps afterwards", () => {
    const options = sourceMapUploadOptions({
      SENTRY_AUTH_TOKEN: TOKEN,
      SENTRY_ORG: "workshop",
      SENTRY_PROJECT: " cabinet ",
      APP_RELEASE: "0f1e2d3",
    });

    expect(options).toMatchObject({
      authToken: TOKEN,
      org: "workshop",
      project: "cabinet",
      release: { name: "0f1e2d3", create: true, finalize: true },
      sourcemaps: { deleteSourcemapsAfterUpload: true },
      telemetry: false,
      buildTimeInstrumentation: false,
      routeManifestInjection: false,
    });
  });

  it("creates no release when the build does not know its commit", () => {
    const options = sourceMapUploadOptions({ SENTRY_AUTH_TOKEN: TOKEN });

    expect(options?.release).toEqual({ create: false });
    expect(options?.org).toBeUndefined();
    expect(options?.project).toBeUndefined();
  });
});

describe("warnUploadFailed", () => {
  it("lets the build go on with a warning", () => {
    const warn = vi.spyOn(console, "warn").mockImplementation(() => undefined);

    warnUploadFailed(new Error("sentry.io unreachable"));

    expect(warn).toHaveBeenCalledWith("Sentry source map upload failed: sentry.io unreachable");
    warn.mockRestore();
  });

  it("is the handler of every upload", () => {
    expect(sourceMapUploadOptions({ SENTRY_AUTH_TOKEN: TOKEN })?.errorHandler).toBe(warnUploadFailed);
  });
});
