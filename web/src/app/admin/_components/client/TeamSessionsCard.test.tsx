import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import type { Schema } from "@/api/types";
import { ok } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import { TeamSessionsCard } from "./TeamSessionsCard";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn() } }));

const team: Schema<"ClientMemberSessionList"> = {
  items: [
    {
      user_id: "user_owner",
      role: "owner",
      display_name: "Giulia Rossi",
      masked_login: "+39*******89",
      live_session_count: 2,
      last_seen_at: 1_790_000_000_000_000,
    },
    { user_id: "user_staff", role: "staff", display_name: null, masked_login: "m***o@example.com", live_session_count: 0 },
  ],
};

function renderCard(canEnd: boolean, locale: "en" | "it" = "en") {
  return renderInLocale(<TeamSessionsCard businessId="business_1" timeZone="Europe/Rome" canEnd={canEnd} />, { locale });
}

describe("TeamSessionsCard: a client team's sign-ins on the admin's client page", () => {
  beforeEach(() => {
    vi.mocked(api.GET).mockImplementation((() => ok(team)) as never);
    vi.mocked(api.POST).mockReset();
  });

  it.each(["en", "it"] as const)("lists members with their devices, in %s", async (locale) => {
    const { t, tp } = textsIn(locale);
    renderCard(false, locale);

    expect(await screen.findByText("Giulia Rossi")).toBeTruthy();
    expect(screen.getByText(t("adminSessions.roles.owner"))).toBeTruthy();
    expect(screen.getByText(/m\*\*\*o@example\.com/)).toBeTruthy();
    expect(screen.getByText(t("adminSessions.notSignedIn"))).toBeTruthy();
    expect(screen.getByText(new RegExp(tp("adminSessions.devices", 2)))).toBeTruthy();
    // Without the permission there is nothing to end.
    expect(screen.queryByRole("button", { name: t("adminSessions.endLabel", { name: "Giulia Rossi" }) })).toBeNull();
  });

  it("ends every session of a member after a confirmation", async () => {
    const { t, tp } = textsIn("en");
    vi.mocked(api.POST).mockImplementation((() => ok({ revoked_count: 2 })) as never);
    const user = userEvent.setup();
    renderCard(true);

    await user.click(await screen.findByRole("button", { name: t("adminSessions.endLabel", { name: "Giulia Rossi" }) }));
    const dialog = screen.getByRole("dialog", { name: t("adminSessions.endTitle", { name: "Giulia Rossi" }) });
    await user.click(within(dialog).getByRole("button", { name: t("adminSessions.end") }));

    await waitFor(() =>
      expect(vi.mocked(api.POST)).toHaveBeenCalledWith(
        "/v1/admin/clients/{business_id}/members/{member_user_id}/sessions/revoke",
        { params: { path: { business_id: "business_1", member_user_id: "user_owner" } } },
      ),
    );
    expect(await screen.findByText(tp("adminSessions.ended", 2))).toBeTruthy();
    // A member who is not signed in has nothing to end.
    expect(screen.getAllByRole("button", { name: /End sessions of/ })).toHaveLength(1);
  });
});
