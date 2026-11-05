import { screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import { ChangelogDot } from "@/components/help/HelpSupportSection";
import { answerGet, ok } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import { CHANGELOG } from "../../../../content/changelog";
import { WhatsNewScreen } from "./WhatsNewScreen";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), PATCH: vi.fn(), DELETE: vi.fn() } }));

beforeEach(() => {
  queryCache.clear();
  vi.mocked(api.PUT).mockReset();
  answerGet(() => ok({ seen_tips: [], changelog_read_key: null }));
});

describe("What's new", () => {
  it("has no entries from before the launch", () => {
    expect(CHANGELOG).toEqual([]);
  });

  it.each(["en", "it"] as const)("says plainly that there is nothing to show yet (%s)", (locale) => {
    const { t } = textsIn(locale);
    renderInLocale(<WhatsNewScreen signedIn readKey={null} />, { locale });

    expect(screen.getByRole("heading", { level: 1, name: t("changelog.title") })).toBeTruthy();
    expect(screen.getByText(t("changelog.emptyTitle"))).toBeTruthy();
    expect(screen.getByText(t("changelog.emptyDescription"))).toBeTruthy();
    expect(screen.queryByRole("list")).toBeNull();
    expect(screen.queryByText(t("changelog.newBadge"), { exact: true })).toBeNull();
    expect(api.PUT).not.toHaveBeenCalled();
  });

  it("puts no unread dot on the account button", async () => {
    const { container } = renderInLocale(<ChangelogDot />);

    await waitFor(() => expect(api.GET).toHaveBeenCalled());
    expect(container.querySelector("[data-changelog-dot]")).toBeNull();
  });
});
