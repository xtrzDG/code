import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import type { BusinessSecurityView, BusinessView, CurrentUserView } from "@/api/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import { answerGet, ok } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import { business } from "../../_lib/settingsFixtures";
import { RecordingPermissionCard } from "./RecordingPermissionCard";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn() } }));

const me = { user: { id: "user_owner", is_platform_admin: false } } as unknown as CurrentUserView;
const ownersOnly: BusinessSecurityView = {
  business_id: business.id,
  require_mfa_for_members: false,
  members_without_two_factor: 0,
  viewer_auth_level: "one_factor",
  staff_may_play_recordings: false,
};

function renderCard(viewer: BusinessView = business, locale: "en" | "it" = "en") {
  answerGet((path) =>
    path === "/v1/businesses/{business_id}/security" ? ok(ownersOnly) : Promise.reject(new Error(path)),
  );
  return renderInLocale(
    <BusinessProvider business={viewer} me={me}>
      <RecordingPermissionCard />
    </BusinessProvider>,
    { locale },
  );
}

describe("RecordingPermissionCard: who may play call recordings", () => {
  beforeEach(() => {
    queryCache.clear();
    vi.mocked(api.PUT).mockReset();
  });

  it.each(["en", "it"] as const)("keeps recordings to owners by default (%s)", async (locale) => {
    const { t } = textsIn(locale);
    renderCard(business, locale);

    const toggle = await screen.findByRole("checkbox", { name: t("security.recordings.toggle") });
    expect((toggle as HTMLInputElement).checked).toBe(false);
    expect(screen.getByText(t("security.recordings.off"))).toBeTruthy();
  });

  it("lets the owner allow staff, sending only that choice", async () => {
    const { t } = textsIn("en");
    vi.mocked(api.PUT).mockImplementation((() => ok({ ...ownersOnly, staff_may_play_recordings: true })) as never);
    renderCard();

    await userEvent.click(await screen.findByRole("checkbox", { name: t("security.recordings.toggle") }));

    await waitFor(() => expect(screen.getByText(t("security.recordings.on"))).toBeTruthy());
    expect(vi.mocked(api.PUT).mock.calls[0]?.[1]).toEqual({
      params: { path: { business_id: business.id } },
      body: { staff_may_play_recordings: true },
    });
  });

  it("shows staff the choice without letting them change it", async () => {
    const { t } = textsIn("it");
    renderCard({ ...business, viewer_role: "staff" }, "it");

    const toggle = await screen.findByRole("checkbox", { name: t("security.recordings.toggle") });
    expect((toggle as HTMLInputElement).disabled).toBe(true);
    expect(screen.getByText(t("security.team.ownerOnly"))).toBeTruthy();
  });
});
