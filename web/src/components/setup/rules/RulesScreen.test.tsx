import { screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import { answerGet, pending } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import type { StepContext } from "../flow/stepContext";
import { RulesScreen } from "./RulesScreen";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));

/** Only what the Rules screen reads of the tunnel's context. */
function context(): StepContext {
  return {
    businessId: "business_1",
    wizard: {
      profile: { handoff_rules: [], forbidden: [], tone: null, is_recording_notice_enabled: true },
      steps: [],
      default_handoff_rules: [],
      default_forbidden_rules: [],
    },
    starters: { faq: [], handoff_rules: [], forbidden_rules: [], tone: null },
  } as unknown as StepContext;
}

describe("RulesScreen: call recording lives in Settings → Calls", () => {
  beforeEach(() => {
    queryCache.clear();
    vi.mocked(api.PATCH).mockReset();
    answerGet(() => pending());
  });

  it.each(["en", "it"] as const)("points to Settings → Calls instead of a recording switch (%s)", (locale) => {
    const { t } = textsIn(locale);
    renderInLocale(<RulesScreen ctx={context()} />, { locale });

    // The profile's old notice flag changes nothing a caller hears: no switch for it.
    expect(screen.queryByRole("checkbox")).toBeNull();
    expect(screen.getAllByText(t("profileEdit.rules.recordingNotice"))).toHaveLength(1);
    const link = screen.getByRole("link", { name: t("profileEdit.rules.recordingNoticeLink") });
    expect(link.getAttribute("href")).toBe("/b/business_1/settings/calls");
    // What a rule and the tone may hold is said once, for both.
    expect(screen.getAllByText(t("profileEdit.rules.instructionRule"))).toHaveLength(1);
    expect(api.PATCH).not.toHaveBeenCalled();
  });
});
