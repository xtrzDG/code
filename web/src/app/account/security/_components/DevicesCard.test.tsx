import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import type { Schema } from "@/api/types";
import { signOut } from "@/components/shell/signOut";
import { LOGIN_PATH } from "@/lib/navigation";
import { failure, ok } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import { DevicesCard } from "./DevicesCard";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), DELETE: vi.fn() } }));
vi.mock("@/components/shell/signOut", () => ({ signOut: vi.fn(() => Promise.resolve()) }));

function session(id: string, isCurrent: boolean, kind: "desktop" | "phone") {
  return {
    id,
    is_current: isCurrent,
    created_at: 1_700_000_000_000_000,
    last_seen_at: 1_700_000_100_000_000,
    expires_at: 1_702_000_000_000_000,
    auth_level: "one_factor",
    device: { kind, browser: "Chrome", operating_system: kind === "phone" ? "Android" : "macOS" },
  };
}

const sessions = {
  items: [session("user_session_here", true, "desktop"), session("user_session_phone", false, "phone")],
} as unknown as Schema<"UserSessionList">;

const assign = vi.fn();

async function confirmSignOutEverywhere() {
  const { t } = textsIn("en");
  const user = userEvent.setup();
  await user.click(await screen.findByRole("button", { name: t("devices.endAll") }));
  const dialog = screen.getByRole("dialog", { name: t("devices.endAllTitle") });
  expect(dialog.textContent).toContain(t("devices.endAllDescription"));
  await user.click(within(dialog).getByRole("button", { name: t("devices.endAll") }));
}

describe("DevicesCard: sign out everywhere, this device too", () => {
  beforeEach(() => {
    vi.mocked(api.GET).mockImplementation((() => ok(sessions)) as never);
    vi.mocked(api.POST).mockReset();
    vi.mocked(signOut).mockClear();
    assign.mockReset();
    vi.stubGlobal("location", { ...window.location, assign });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("ends every session, drops this one and opens the sign-in page", async () => {
    vi.mocked(api.POST).mockImplementation((() => ok({ revoked_count: 2 })) as never);
    renderInLocale(<DevicesCard isPlatformAdmin={false} />);

    await confirmSignOutEverywhere();

    await waitFor(() => expect(assign).toHaveBeenCalledWith(LOGIN_PATH));
    expect(vi.mocked(api.POST)).toHaveBeenCalledWith("/v1/me/sessions/revoke-all");
    expect(vi.mocked(signOut)).toHaveBeenCalledOnce();
  });

  it("keeps the person here when the API refuses", async () => {
    vi.mocked(api.POST).mockImplementation((() => failure(503, { error: "unavailable", message: "Down." })) as never);
    renderInLocale(<DevicesCard isPlatformAdmin={false} />);

    await confirmSignOutEverywhere();

    await waitFor(() => expect(vi.mocked(api.POST)).toHaveBeenCalledOnce());
    expect(vi.mocked(signOut)).not.toHaveBeenCalled();
    expect(assign).not.toHaveBeenCalled();
    expect(screen.getByRole("dialog")).toBeTruthy();
  });

  it.each(["en", "it"] as const)("offers it next to signing out the others, in %s", async (locale) => {
    const { t } = textsIn(locale);
    renderInLocale(<DevicesCard isPlatformAdmin={false} />, { locale });

    expect(await screen.findByRole("button", { name: t("devices.endAll") })).toBeTruthy();
    expect(screen.getByRole("button", { name: t("devices.endOthers") })).toBeTruthy();
  });
});
