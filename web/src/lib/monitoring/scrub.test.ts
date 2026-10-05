import { describe, expect, it } from "vitest";

import { readDsn, readRelease, readSampleRate, serverOptions, DEFAULT_TRACES_SAMPLE_RATE } from "./options";
import { redactText, scrubEvent, type MonitoringEvent } from "./scrub";

describe("scrubEvent", () => {
  it("drops the request, the user and the breadcrumbs", () => {
    const event: MonitoringEvent = {
      request: { cookies: { aw_session: "secret" }, data: "body" },
      user: { email: "owner@example.com" },
      breadcrumbs: [{ message: "typed something" }],
      transaction: "/b/[businessId]/conversations?search=Anna",
    };

    const scrubbed = scrubEvent(event);

    expect(scrubbed).toEqual({ transaction: "/b/[businessId]/conversations" });
  });

  it("masks e-mail addresses and phone numbers in error texts", () => {
    const event: MonitoringEvent = {
      message: "Could not invite anna@example.com",
      exception: { values: [{ value: "Booking for +995 599 12-34-56 failed" }, {}] },
    };

    scrubEvent(event);

    expect(event.message).toBe("Could not invite [email]");
    expect(event.exception?.values?.[0]?.value).toBe("Booking for [number] failed");
  });

  it("masks the keys of guests' booking links", () => {
    const token = "AbCdEfGhIjKlMnOpQrStUvWxYz0123456789_-AbCdEf";
    const event: MonitoringEvent = {
      transaction: `/r/${token}`,
      message: `GET /api/backend/v1/public/bookings/${token}/slots failed`,
    };

    scrubEvent(event);

    expect(event.transaction).toBe("/r/[token]");
    expect(event.message).toBe("GET /api/backend/v1/public/bookings/[token]/slots failed");
  });

  it("keeps short numbers such as statuses and counts", () => {
    expect(redactText("HTTP 503 after 3 tries")).toBe("HTTP 503 after 3 tries");
  });
});

describe("monitoring options", () => {
  it("sends nothing without a DSN", () => {
    expect(serverOptions({})).toBeNull();
    expect(readDsn({ SENTRY_DSN: "  " })).toBeNull();
  });

  it("names the release, the environment and the sample rate", () => {
    const options = serverOptions({
      SENTRY_DSN: "https://key@o1.ingest.de.sentry.io/42",
      NODE_ENV: "production",
      RENDER_GIT_COMMIT: "4718714",
      SENTRY_TRACES_SAMPLE_RATE: "0.2",
    });

    expect(options).toMatchObject({
      dsn: "https://key@o1.ingest.de.sentry.io/42",
      environment: "production",
      release: "4718714",
      tracesSampleRate: 0.2,
      sendDefaultPii: false,
    });
    expect(options?.beforeSend).toBe(scrubEvent);
  });

  it("prefers APP_RELEASE and falls back on bad sample rates", () => {
    expect(readRelease({ APP_RELEASE: "2026.10.1", RENDER_GIT_COMMIT: "4718714" })).toBe("2026.10.1");
    expect(readRelease({})).toBeUndefined();
    expect(readSampleRate(undefined)).toBe(DEFAULT_TRACES_SAMPLE_RATE);
    expect(readSampleRate("1.5")).toBe(DEFAULT_TRACES_SAMPLE_RATE);
    expect(readSampleRate("nope")).toBe(DEFAULT_TRACES_SAMPLE_RATE);
    expect(readSampleRate("0")).toBe(0);
    expect(serverOptions({ SENTRY_DSN: "https://key@sentry.example/1" })?.environment).toBe("production");
  });
});
