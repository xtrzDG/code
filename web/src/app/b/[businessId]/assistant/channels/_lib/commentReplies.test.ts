import { describe, expect, it } from "vitest";

import { addKeyword, buildCommentRepliesBody, commentRepliesForm, isSavedReplies, MAX_KEYWORDS } from "./commentReplies";

const saved = { is_on: true, is_available: false, keywords: ["menu", "price list"], reply_text: "Here is our menu." };

describe("keywords of replies to comments", () => {
  it("are trimmed, folded to one space and kept once in any letter case", () => {
    expect(addKeyword(["menu"], "  price   list ")).toEqual({ keywords: ["menu", "price list"], problem: null });
    expect(addKeyword(["menu"], "MENU")).toEqual({ keywords: ["menu"], problem: null });
    expect(addKeyword(["ფასი"], "ფასი")).toEqual({ keywords: ["ფასი"], problem: null });
  });

  it("refuse an empty, multi-line or too long word, and more than twenty", () => {
    expect(addKeyword([], "   ").problem).toBe("keyword");
    expect(addKeyword([], "menu\nprice").problem).toBe("keyword");
    expect(addKeyword([], "x".repeat(51)).problem).toBe("keyword");
    expect(addKeyword([], "x".repeat(50)).problem).toBeNull();
    const full = Array.from({ length: MAX_KEYWORDS }, (_, index) => `word${index}`);
    expect(addKeyword(full, "one more")).toEqual({ keywords: full, problem: "tooMany" });
  });
});

describe("the body that saves replies to comments", () => {
  it("needs a keyword and a message when turned on", () => {
    expect(buildCommentRepliesBody({ isOn: true, keywords: [], replyText: "  " })).toEqual({
      ok: false,
      problems: ["keywordsMissing", "replyMissing"],
    });
    expect(buildCommentRepliesBody({ isOn: true, keywords: ["menu"], replyText: " Hi " })).toEqual({
      ok: true,
      body: { is_on: true, keywords: ["menu"], reply_text: "Hi" },
    });
  });

  it("keeps what was typed when turned off, even half done", () => {
    expect(buildCommentRepliesBody({ isOn: false, keywords: [], replyText: "" })).toEqual({
      ok: true,
      body: { is_on: false, keywords: [], reply_text: null },
    });
  });

  it("is needed only when the form differs from what is saved", () => {
    const form = commentRepliesForm(saved);

    expect(form).toEqual({ isOn: true, keywords: ["menu", "price list"], replyText: "Here is our menu." });
    expect(isSavedReplies(form, saved)).toBe(true);
    expect(isSavedReplies({ ...form, replyText: "Here is our menu.  " }, saved)).toBe(true);
    expect(isSavedReplies({ ...form, isOn: false }, saved)).toBe(false);
    expect(isSavedReplies({ ...form, keywords: ["price list", "menu"] }, saved)).toBe(false);
    expect(isSavedReplies({ ...form, keywords: ["menu"] }, saved)).toBe(false);
    expect(commentRepliesForm({ is_on: false, is_available: true })).toEqual({ isOn: false, keywords: [], replyText: "" });
  });
});
