import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { queryCache } from "@/api/queryCache";
import type { BusinessView, CurrentUserView, Schema } from "@/api/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import { answerGet, ok, pending } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import type { TextBackView } from "../_lib/calls";
import { CallsTab } from "./CallsTab";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), PUT: vi.fn(), POST: vi.fn() } }));

const business = {
  id: "business_1",
  name: "Trattoria del Sole",
  viewer_role: "owner",
  status: "live",
  currency_code: "EUR",
  timezone: "Europe/Rome",
} as unknown as BusinessView;
const me = { user: { id: "user_owner", is_platform_admin: false } } as unknown as CurrentUserView;

const settings = {
  is_summary_enabled: true,
  is_text_back_enabled: false,
  is_sms_fallback_enabled: false,
  is_sms_available: true,
  is_whatsapp_connected: false,
  is_recording_enabled: false,
  is_staff_transfer_confirmed: false,
  text_back_template_name: null,
  transfer_phone_number: null,
  template_previews: [
    { language: "it", template_body: "Ciao, abbiamo perso la tua chiamata a {{1}}.", example: "" },
    { language: "en", template_body: "Hi, we missed your call at {{1}}.", example: "" },
  ],
} as unknown as Schema<"CallSettingsView">;

const missed = { id: "missed_call_1", reason: "busy", called_at: 1_790_000_000_000_000, status: "sent" } as unknown as TextBackView;

function answer(view: Schema<"CallSettingsView">, textBacks: "pending" | TextBackView[]) {
  answerGet((path) =>
    path === "/v1/businesses/{business_id}/call-settings"
      ? ok(view)
      : textBacks === "pending"
        ? pending()
        : ok({ items: textBacks, next_cursor: null }),
  );
}

function renderTab(locale: "en" | "it" = "en") {
  return renderInLocale(
    <BusinessProvider business={business} me={me}>
      <CallsTab />
    </BusinessProvider>,
    { locale },
  );
}

const row = (name: string) => screen.getByRole("button", { name: new RegExp(`^${name}`) });

describe("CallsTab on a phone", () => {
  beforeEach(() => queryCache.clear());
  afterEach(() => window.localStorage.clear());

  it.each(["en", "it"] as const)("folds the recording, the template texts and the latest text-backs into rows, in %s", async (locale) => {
    const { t, tp } = textsIn(locale);
    answer(settings, [missed, { ...missed, id: "missed_call_2" }, { ...missed, id: "missed_call_3" }]);
    renderTab(locale);

    const recording = await waitFor(() => row(t("callSettings.recording.title")));
    expect(recording.textContent).toContain(t("callSettings.recording.stateOff"));
    expect(row(t("callSettings.template.title")).textContent).toContain(tp("callSettings.template.languages", 2));
    await waitFor(() => expect(row(t("callSettings.history.title")).textContent).toContain("3"));
    for (const name of ["recording.title", "template.title", "history.title"] as const) {
      expect(row(t(`callSettings.${name}`)).getAttribute("aria-expanded"), name).toBe("false");
    }
    // The switches people come for stay open: the summaries, the text-backs and the transfers are no rows.
    for (const name of ["summaries.title", "textBack.title", "transfers.title"] as const) {
      expect(screen.queryByRole("button", { name: new RegExp(`^${t(`callSettings.${name}`)}`) }), name).toBeNull();
    }
  });

  it("says the recording is on, opens a row on a tap and remembers it for the owner", async () => {
    const user = userEvent.setup();
    const { t } = textsIn("en");
    answer({ ...settings, is_recording_enabled: true }, "pending");
    const view = renderTab();

    const recording = await waitFor(() => row(t("callSettings.recording.title")));
    expect(recording.textContent).toContain(t("callSettings.recording.stateOn"));
    // The history still loads: its row says no count yet.
    expect(row(t("callSettings.history.title")).textContent).toBe(t("callSettings.history.title"));

    await user.click(recording);
    expect(recording.getAttribute("aria-expanded")).toBe("true");
    const body = document.getElementById(recording.getAttribute("aria-controls")!)!;
    expect(body.className).not.toContain("max-lg:hidden");
    expect(body.textContent).toContain(t("callSettings.recording.noticeRecorded"));
    expect(window.localStorage.getItem("aw.pref.settings-calls-open:user_owner")).toBe("recording");

    view.unmount();
    renderTab();
    expect((await waitFor(() => row(t("callSettings.recording.title")))).getAttribute("aria-expanded")).toBe("true");
  });
});
