import { act } from "@testing-library/react";
import type { ReactNode } from "react";
import { hydrateRoot } from "react-dom/client";
import { renderToString } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { AccountSecurityView } from "@/api/types";
import { ViewerTimeZoneProvider } from "@/components/time/ViewerTimeZone";
import { Providers } from "@/test/render";

import { AuthenticatorCard } from "./AuthenticatorCard";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));

// 22:30 UTC: already the next day in Tbilisi (UTC+4), still the same day in Berlin.
const CONFIRMED_AT = Date.UTC(2026, 2, 14, 22, 30) * 1000;
const LAST_USED_AT = Date.UTC(2026, 9, 4, 21, 5) * 1000;

const security: AccountSecurityView = {
  is_mfa_required: false,
  recovery_codes_left: 8,
  step_up_max_age_seconds: 300,
  totp_status: "active",
  totp_confirmed_at: CONFIRMED_AT,
  totp_last_used_at: LAST_USED_AT,
};

function Card({ zone }: { zone: string | null }): ReactNode {
  return (
    <Providers locale="ru">
      <ViewerTimeZoneProvider initialZone={zone}>
        <AuthenticatorCard security={security} account="owner@example.com" onChanged={async () => undefined} />
      </ViewerTimeZoneProvider>
    </Providers>
  );
}

function textOf(html: string): string {
  const container = document.createElement("div");
  container.innerHTML = html;
  return container.textContent ?? "";
}

function renderOnServerIn(processZone: string, zone: string | null): string {
  process.env.TZ = processZone;
  return renderToString(<Card zone={zone} />);
}

describe("AuthenticatorCard renders the same text whatever the process's zone", () => {
  afterEach(() => {
    process.env.TZ = "UTC";
  });

  it("moves the process's clock (the check below would prove nothing otherwise)", () => {
    process.env.TZ = "UTC";
    const utcHours = new Date(CONFIRMED_AT / 1000).getHours();
    process.env.TZ = "Asia/Tbilisi";
    expect(new Date(CONFIRMED_AT / 1000).getHours()).not.toBe(utcHours);
  });

  it.each([["Asia/Tbilisi"], ["Europe/Berlin"], [null]])("with the reader's zone %s", (zone) => {
    const inUtc = renderOnServerIn("UTC", zone);
    const inTbilisi = renderOnServerIn("Asia/Tbilisi", zone);

    expect(inTbilisi).toBe(inUtc);
  });

  it("dates the factor in the reader's zone, not the server's", () => {
    const berlin = renderOnServerIn("Asia/Tbilisi", "Europe/Berlin");
    const tbilisi = renderOnServerIn("UTC", "Asia/Tbilisi");

    expect(textOf(berlin)).toMatch(/14 мар/);
    expect(textOf(tbilisi)).toMatch(/15 мар/);
  });

  it("hydrates in a browser in another zone without a mismatch", async () => {
    const html = renderOnServerIn("UTC", "Europe/Berlin");
    process.env.TZ = "Asia/Tbilisi";
    const container = document.createElement("div");
    container.innerHTML = html;
    document.body.append(container);
    const recoverable = vi.fn();
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);

    await act(async () => {
      hydrateRoot(container, <Card zone="Europe/Berlin" />, { onRecoverableError: recoverable });
    });

    expect(recoverable).not.toHaveBeenCalled();
    expect(consoleError.mock.calls.flat().join(" ")).not.toMatch(/hydrat|did not match|#418/i);
  });
});
