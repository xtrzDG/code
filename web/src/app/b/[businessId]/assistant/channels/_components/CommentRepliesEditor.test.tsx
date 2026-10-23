import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "@/api/client";
import { queryCache } from "@/api/queryCache";
import type { CurrentUserView } from "@/api/types";
import { BusinessProvider } from "@/components/business/BusinessContext";
import { ok } from "@/test/fakeApi";
import { renderInLocale, textsIn } from "@/test/render";

import { business } from "../../../settings/_lib/settingsFixtures";
import type { ChannelView } from "../_lib/channels";
import { CommentRepliesEditor } from "./CommentRepliesEditor";

vi.mock("@/api/client", () => ({ api: { GET: vi.fn(), POST: vi.fn(), PUT: vi.fn(), DELETE: vi.fn() } }));

const me = { user: { id: "user_owner", is_platform_admin: false } } as unknown as CurrentUserView;

function instagram(replies: ChannelView["comment_replies"]): ChannelView {
  return {
    id: "channel_1",
    business_id: business.id,
    channel: "instagram",
    status: "connected",
    account_id: "17841400000000001",
    has_credential: true,
    updated_at: 0,
    comment_replies: replies,
  } as ChannelView;
}

function show(channel: ChannelView, canManage = true, locale: "en" | "he" = "en") {
  renderInLocale(
    <BusinessProvider business={business} me={me}>
      <CommentRepliesEditor channel={channel} canManage={canManage} />
    </BusinessProvider>,
    { locale },
  );
}

beforeEach(() => {
  queryCache.clear();
  vi.mocked(api.PUT).mockReset();
});

describe("replies to comments on the Instagram card", () => {
  it("are turned on with keywords and a message, and saved", async () => {
    const t = textsIn("en").t;
    vi.mocked(api.PUT).mockImplementation((() =>
      ok(instagram({ is_on: true, is_available: true, keywords: ["menu"], reply_text: "Our menu" }))) as never);
    show(instagram({ is_on: false, is_available: true, keywords: [], reply_text: null }));
    const user = userEvent.setup();

    await user.click(screen.getByRole("switch", { name: t("metaConnect.commentReplies.toggle") }));
    await user.click(screen.getByRole("button", { name: t("metaConnect.commentReplies.save") }));
    expect(screen.getByText(t("metaConnect.commentReplies.errors.keywordsMissing"))).toBeTruthy();
    expect(screen.getByText(t("metaConnect.commentReplies.errors.replyMissing"))).toBeTruthy();
    expect(api.PUT).not.toHaveBeenCalled();

    const keyword = screen.getByRole("textbox", { name: t("metaConnect.commentReplies.keywords") });
    await user.type(keyword, "menu{Enter}");
    await user.type(keyword, "MENU{Enter}");
    await user.type(screen.getByRole("textbox", { name: t("metaConnect.commentReplies.replyText") }), "Our menu");
    await user.click(screen.getByRole("button", { name: t("metaConnect.commentReplies.save") }));

    await waitFor(() => expect(api.PUT).toHaveBeenCalledTimes(1));
    expect(vi.mocked(api.PUT).mock.calls[0]?.[1]).toMatchObject({
      params: { path: { business_id: business.id } },
      body: { is_on: true, keywords: ["menu"], reply_text: "Our menu" },
    });
    expect(await screen.findByText(t("metaConnect.commentReplies.savedToast"))).toBeTruthy();
  });

  it("removes a keyword and refuses one that is too long", async () => {
    const t = textsIn("en").t;
    show(instagram({ is_on: true, is_available: true, keywords: ["menu", "price"], reply_text: "Hi" }));
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: t("metaConnect.commentReplies.removeKeyword", { keyword: "menu" }) }));
    await user.type(screen.getByRole("textbox", { name: t("metaConnect.commentReplies.keywords") }), `${"x".repeat(51)}{Enter}`);

    expect(screen.queryByText("menu")).toBeNull();
    expect(screen.getByText(t("metaConnect.commentReplies.errors.keyword"))).toBeTruthy();
  });

  it("say they wait for the next update, and staff only read them (in Hebrew too)", () => {
    const t = textsIn("he").t;
    show(instagram({ is_on: true, is_available: false, keywords: ["תפריט"], reply_text: "שלום" }), false, "he");

    expect(screen.getByText(t("metaConnect.commentReplies.unavailable"))).toBeTruthy();
    expect(screen.getByText(t("metaConnect.commentReplies.summaryOn", { keywords: "תפריט" }))).toBeTruthy();
    expect(screen.queryByRole("switch")).toBeNull();
    expect(screen.queryByRole("button", { name: t("metaConnect.commentReplies.save") })).toBeNull();
  });

  it("show nothing on a channel without them", () => {
    show(instagram(null));
    expect(screen.queryByRole("region")).toBeNull();
  });
});
