import { waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import type { Schema } from "@/api/types";
import { answerGet, ok, pending } from "@/test/fakeApi";
import { formatMoney } from "@/lib/format";
import { renderInLocale, textsIn } from "@/test/render";

import type { AdminClientSummary } from "../../_lib/clients";
import type { ClientQuality } from "../../_lib/quality";
import { useClientFolds, type ClientFolds } from "./clientFolds";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn() } }));

const team: Schema<"ClientMemberSessionList"> = {
  items: [
    { user_id: "user_owner", role: "owner", display_name: "Giulia Rossi", masked_login: "+39*******89", live_session_count: 2 },
    { user_id: "user_staff", role: "staff", display_name: "Marco", masked_login: "m***o@example.com", live_session_count: 1 },
    { user_id: "user_away", role: "staff", display_name: null, masked_login: "a***y@example.com", live_session_count: 0 },
  ],
};

const quality = {
  business_id: "business_1",
  days: [],
  sample_count: 8,
  average_score: 4.62,
  is_dropping: false,
  drop_percent: 0,
} as unknown as ClientQuality;

function client(overrides: Partial<AdminClientSummary> = {}): AdminClientSummary {
  return {
    reply_speed: { reply_count: 48, p50_ms: 7_500, p95_ms: 11_000, channels: [] },
    guard_activity: { checked_replies: 50, rewritten_replies: 1, handed_off_replies: 1, injection_flags: 0 },
    cost: { margin: { amount_minor: 1250, currency_code: "GEL" } },
    ...overrides,
  } as unknown as AdminClientSummary;
}

function answer(qualityView: ClientQuality = quality) {
  answerGet((path) =>
    path === "/v1/admin/clients/{business_id}/members"
      ? ok(team)
      : path === "/v1/admin/clients/{business_id}/quality"
        ? ok(qualityView)
        : pending(),
  );
}

function Probe({ summary }: { summary: AdminClientSummary }) {
  const folds = useClientFolds("business_1", summary);
  return (
    <ul>
      {(Object.keys(folds) as (keyof ClientFolds)[]).map((name) => (
        <li key={name} data-fold={name}>
          {folds[name]}
        </li>
      ))}
    </ul>
  );
}

const fold = (name: keyof ClientFolds) => document.querySelector<HTMLElement>(`[data-fold="${name}"]`)!;
const said = (name: keyof ClientFolds) => ({
  text: fold(name).textContent,
  tone: fold(name).querySelector("span")?.className ?? null,
});

describe("useClientFolds: what the client page's folded rows say on a phone", () => {
  beforeEach(() => {
    queryCache.clear();
    answer();
  });

  it.each(["en", "it"] as const)("says the figure of each card, in %s", async (locale) => {
    const { t, tp } = textsIn(locale);
    renderInLocale(<Probe summary={client()} />, { locale });

    expect(said("replySpeed")).toEqual({
      text: t("adminReplySpeed.fold", { wait: t("adminReplySpeed.seconds", { value: locale === "it" ? "7,5" : "7.5" }) }),
      tone: null,
    });
    // 2 of 50 checked replies held back.
    expect(said("replyGuard")).toEqual({ text: t("adminReplyGuard.fold", { share: "4%" }), tone: null });
    expect(said("cost")).toEqual({ text: t("admin.detail.marginFold", { margin: formatMoney(1250, "GEL", locale) }), tone: null });
    // Two of the three members are signed in somewhere.
    await waitFor(() => expect(said("sessions")).toEqual({ text: tp("adminSessions.signedIn", 2), tone: null }));
    await waitFor(() =>
      expect(said("quality")).toEqual({ text: t("quality.admin.scoreValue", { score: locale === "it" ? "4,6" : "4.6" }), tone: null }),
    );
  });

  it("colours what the cards themselves raise: replies held back often, a dropping score, a loss", async () => {
    const { t } = textsIn("en");
    answer({ ...quality, is_dropping: true, drop_percent: 15 });
    renderInLocale(
      <Probe
        summary={client({
          guard_activity: { checked_replies: 20, rewritten_replies: 3, handed_off_replies: 3, injection_flags: 0 },
          cost: { margin: { amount_minor: -40, currency_code: "GEL" } } as AdminClientSummary["cost"],
        })}
      />,
    );
    expect(said("replyGuard")).toEqual({ text: t("adminReplyGuard.fold", { share: "30%" }), tone: "text-danger" });
    expect(said("cost")).toEqual({ text: t("admin.detail.marginFold", { margin: formatMoney(-40, "GEL", "en") }), tone: "text-danger" });
    await waitFor(() => expect(said("quality").tone).toBe("text-warning"));
  });

  it("says nothing it does not know: no measured replies, nothing checked, no margin, nothing judged, the team still loading", async () => {
    answerGet((path) => (path === "/v1/admin/clients/{business_id}/quality" ? ok({ ...quality, sample_count: 0 }) : pending()));
    renderInLocale(
      <Probe
        summary={client({
          reply_speed: { reply_count: 0, channels: [] } as unknown as AdminClientSummary["reply_speed"],
          guard_activity: undefined,
          cost: { margin: null } as unknown as AdminClientSummary["cost"],
        })}
      />,
    );
    await waitFor(() => expect(vi.mocked(api.GET)).toHaveBeenCalledTimes(2));
    for (const name of ["replySpeed", "replyGuard", "cost", "quality", "sessions"] as const) {
      expect(fold(name).textContent, name).toBe("");
    }
  });
});
