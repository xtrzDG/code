import { act, fireEvent, screen, within } from "@testing-library/react";
import type { ReactNode } from "react";
import { hydrateRoot } from "react-dom/client";
import { renderToString } from "react-dom/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import type { PasskeyListView } from "@/api/types";
import { ViewerTimeZoneProvider } from "@/components/time/ViewerTimeZone";
import type * as PasskeyCeremony from "@/lib/security/passkeyCeremony";
import { createPasskey } from "@/lib/security/passkeyCeremony";
import { Providers, renderInLocale, textsIn } from "@/test/render";

import { PasskeysCard } from "./PasskeysCard";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));
vi.mock("@/lib/security/passkeyCeremony", async (importOriginal) => ({
  ...(await importOriginal<typeof PasskeyCeremony>()),
  createPasskey: vi.fn(),
}));

/** What openapi-fetch resolves to for a 200. */
function answer(data: unknown): never {
  return Promise.resolve({ data, response: new Response(null, { status: 200 }) }) as never;
}

const ADDED_AT = Date.UTC(2026, 8, 1, 9) * 1000;

const LIST: PasskeyListView = {
  is_available: true,
  is_recommended: false,
  items: [
    {
      id: "passkey_1",
      name: "MacBook Touch ID",
      created_at: ADDED_AT,
      last_used_at: null,
      is_synced: true,
      is_backed_up: true,
      clone_suspected_at: null,
      transports: ["internal"],
    },
    {
      id: "passkey_2",
      name: "YubiKey",
      created_at: ADDED_AT,
      last_used_at: ADDED_AT,
      is_synced: false,
      is_backed_up: false,
      clone_suspected_at: ADDED_AT,
      transports: ["usb"],
    },
  ],
};

function Card({ list = LIST }: { list?: PasskeyListView }): ReactNode {
  return (
    <ViewerTimeZoneProvider initialZone="Asia/Tbilisi">
      <PasskeysCard initial={list} account="owner@example.com" onChanged={async () => undefined} />
    </ViewerTimeZoneProvider>
  );
}

function withWebAuthn() {
  vi.stubGlobal("PublicKeyCredential", class {});
  vi.stubGlobal("navigator", { ...navigator, credentials: { create: vi.fn(), get: vi.fn() } });
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.mocked(api.POST).mockReset();
  vi.mocked(api.GET).mockReset();
  document.body.innerHTML = "";
});

describe("PasskeysCard", () => {
  it("lists the passkeys with their state", () => {
    withWebAuthn();
    renderInLocale(<Card />, { locale: "it" });
    const t = textsIn("it").t;

    expect(screen.getByText("MacBook Touch ID")).toBeTruthy();
    expect(screen.getByText(t("passkeys.synced"))).toBeTruthy();
    expect(screen.getByText(t("passkeys.suspended"))).toBeTruthy();
    expect(screen.getByRole("button", { name: t("passkeys.add") })).toBeTruthy();
    expect(screen.getByRole("button", { name: t("passkeys.renameLabel", { name: "YubiKey" }) })).toBeTruthy();
  });

  it("says when this browser cannot use passkeys, and offers no button", () => {
    vi.stubGlobal("PublicKeyCredential", undefined);
    renderInLocale(<Card />, { locale: "en" });
    const t = textsIn("en").t;

    expect(screen.getByText(t("passkeys.unsupported"))).toBeTruthy();
    expect(screen.queryByRole("button", { name: t("passkeys.add") })).toBeNull();
  });

  it("says when the server has no passkeys set up", () => {
    withWebAuthn();
    renderInLocale(<Card list={{ is_available: false, is_recommended: false, items: [] }} />, { locale: "en" });
    const t = textsIn("en").t;

    expect(screen.getByText(t("passkeys.unavailable"))).toBeTruthy();
    expect(screen.queryByRole("button", { name: t("passkeys.add") })).toBeNull();
  });

  it("hydrates in a browser with passkeys without a mismatch", async () => {
    const html = renderToString(
      <Providers locale="en">
        <Card />
      </Providers>,
    );
    // The server cannot know: it claims neither support nor its absence.
    expect(html).not.toContain(textsIn("en").t("passkeys.unsupported"));
    withWebAuthn();
    const container = document.createElement("div");
    container.innerHTML = html;
    document.body.append(container);
    const recoverable = vi.fn();
    const consoleError = vi.spyOn(console, "error").mockImplementation(() => undefined);

    await act(async () => {
      hydrateRoot(
        container,
        <Providers locale="en">
          <Card />
        </Providers>,
        { onRecoverableError: recoverable },
      );
    });

    expect(recoverable).not.toHaveBeenCalled();
    expect(consoleError.mock.calls.flat().join(" ")).not.toMatch(/hydrat|did not match|#418/i);
    expect(container.textContent).toContain(textsIn("en").t("passkeys.add"));
  });

  it("shows the first second factor's recovery codes first, and says the passkey was added once they are put away", async () => {
    withWebAuthn();
    const codes = Array.from({ length: 10 }, (_, index) => `test-code-000${index}`);
    vi.mocked(api.POST)
      .mockReturnValueOnce(answer({ passkey_challenge_id: "challenge_1", options: {} }))
      .mockReturnValueOnce(answer({ passkey: LIST.items?.[0], recovery_codes: codes }));
    vi.mocked(api.GET).mockReturnValue(answer(LIST));
    vi.mocked(createPasskey).mockResolvedValue({} as never);
    renderInLocale(<Card list={{ ...LIST, items: [] }} />, { locale: "en" });
    const t = textsIn("en").t;

    fireEvent.click(screen.getByRole("button", { name: t("passkeys.add") }));
    const dialog = await screen.findByRole("dialog", { name: t("mfa.recovery.title") });
    expect(screen.queryByText(t("passkeys.added"))).toBeNull();
    fireEvent.click(within(dialog).getByRole("checkbox", { name: t("mfa.recovery.saved") }));
    fireEvent.click(within(dialog).getByRole("button", { name: t("common.done") }));

    expect(await screen.findByText(t("passkeys.added"))).toBeTruthy();
  });

  it("says a further passkey was added at once", async () => {
    withWebAuthn();
    vi.mocked(api.POST)
      .mockReturnValueOnce(answer({ passkey_challenge_id: "challenge_2", options: {} }))
      .mockReturnValueOnce(answer({ passkey: LIST.items?.[0], recovery_codes: null }));
    vi.mocked(api.GET).mockReturnValue(answer(LIST));
    vi.mocked(createPasskey).mockResolvedValue({} as never);
    renderInLocale(<Card />, { locale: "en" });
    const t = textsIn("en").t;

    fireEvent.click(screen.getByRole("button", { name: t("passkeys.add") }));

    expect(await screen.findByText(t("passkeys.added"))).toBeTruthy();
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
