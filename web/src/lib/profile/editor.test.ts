import { describe, expect, it } from "vitest";

import type { KnowledgeItemDetails, OpeningInterval, WizardQuestionView } from "@/api/types";

import { answersPatch } from "./answers";
import { freeLinkKinds, LINK_KINDS, linkProblems, linkRowsFrom, linksPayload } from "./links";
import { newFaqSuggestions, newSuggestions, sameText, unansweredQuestions, withAllSuggestions, withRule } from "./rules";
import { groupWeek, knowledgeCounts, weekSummary } from "./summary";

const interval = (weekday: OpeningInterval["weekday"], opens: string, closes: string): OpeningInterval => {
  const minutes = (text: string) => Number(text.slice(0, 2)) * 60 + Number(text.slice(3));
  return { weekday, opens_at: minutes(opens), closes_at: closes === "24:00" ? 1440 : minutes(closes) };
};

describe("week summary", () => {
  const weekdays = ([1, 2, 3, 4, 5] as const).map((day) => interval(day, "10:00", "23:00"));

  it("runs neighbouring days with the same hours together", () => {
    const groups = groupWeek([...weekdays, interval(6, "11:00", "15:00"), interval(6, "16:00", "24:00")]);
    expect(groups.map((group) => [group.from, group.to])).toEqual([
      [1, 5],
      [6, 6],
    ]);
  });

  it("says the week in one line, overnight and round-the-clock hours included", () => {
    expect(weekSummary(weekdays, "en", "24 h")).toBe("Mon–Fri 10:00–23:00");
    // Friday past midnight is stored as Friday to 24:00 plus Saturday to 02:00.
    const late = [interval(5, "18:00", "24:00"), interval(6, "00:00", "02:00")];
    expect(weekSummary(late, "en", "24 h")).toBe("Fri 18:00–02:00");
    expect(weekSummary([interval(7, "00:00", "24:00")], "en", "24 h")).toBe("Sun 24 h");
    expect(weekSummary([interval(1, "09:00", "13:00"), interval(3, "09:00", "13:00")], "en", "24 h")).toBe("Mon 09:00–13:00 · Wed 09:00–13:00");
    expect(weekSummary([], "en", "24 h")).toBe("");
  });
});

describe("knowledge counts", () => {
  const item = (kind: KnowledgeItemDetails["kind"], price: number | null, isActive = true) => ({ kind, price_minor: price, is_active: isActive });

  it("count what is on offer, what has a price and the ready answers", () => {
    expect(knowledgeCounts([item("menu_item", 1800), item("menu_item", null), item("package", 9000, false), item("faq", null), item("policy", null)])).toEqual({
      offers: 2,
      priced: 1,
      questions: 1,
    });
  });
});

describe("answers patch", () => {
  const question = (key: string, answerType: WizardQuestionView["question"]["answer_type"]): WizardQuestionView => ({
    question: { key, fact_key: key, step: "offer", answer_type: answerType, is_required: false, label: key },
  });

  it("names every question of the screen, so a cleared answer is cleared", () => {
    const questions = [question("cuisine", "short_text"), question("parking", "yes_no"), question("diets", "multiple_choice"), question("notes", "long_text")];
    expect(answersPatch(questions, { cuisine: { text: "  Georgian ", choices: [] }, parking: { text: "", choices: [] }, diets: { text: "", choices: ["vegan"] } })).toEqual([
      { question_key: "cuisine", answer: "Georgian" },
      { question_key: "parking", answer: null },
      { question_key: "diets", choice_keys: ["vegan"] },
      { question_key: "notes", answer: null },
    ]);
    expect(answersPatch([question("diets", "single_choice")], {})).toEqual([{ question_key: "diets", choice_keys: [] }]);
  });
});

describe("links", () => {
  it("are one row per kind, checked and saved without the empty ones", () => {
    const rows = linkRowsFrom([{ kind: "menu", url: "https://example.com/menu" }]);
    expect(rows).toEqual([{ key: "link-menu", kind: "menu", url: "https://example.com/menu" }]);
    expect(freeLinkKinds(rows)).toEqual(LINK_KINDS.filter((kind) => kind !== "menu"));
    expect(linkRowsFrom(undefined)).toEqual([]);

    const typed = [...rows, { key: "new-1", kind: "map" as const, url: "maps" }, { key: "new-2", kind: "website" as const, url: "  " }];
    expect(linkProblems(typed)).toEqual({ "new-1": "validation.url" });
    expect(linksPayload([...rows, { key: "new-3", kind: "website", url: " https://example.com " }, typed[2]!])).toEqual([
      { kind: "menu", url: "https://example.com/menu" },
      { kind: "website", url: "https://example.com" },
    ]);
  });
});

describe("starter suggestions", () => {
  it("are new until the owner has the same words on their list", () => {
    expect(sameText(" A  complaint ", "a complaint")).toBe(true);
    expect(newSuggestions(["A complaint"], ["a complaint", "A banquet", "a banquet", " "])).toEqual(["A banquet"]);
    expect(withRule(["A complaint"], " A banquet ")).toEqual(["A complaint", "A banquet"]);
    expect(withRule(["A complaint"], "a COMPLAINT")).toEqual(["A complaint"]);
    expect(withAllSuggestions(["A complaint"], ["A banquet ", "A complaint", "Refunds"])).toEqual(["A complaint", "A banquet", "Refunds"]);
  });

  it("leave out the frequent questions the business already answers", () => {
    const parking = { key: "parking", question: "Is there parking?", answer: "Yes, in the yard.", is_ready: true };
    const delivery = { key: "delivery", question: "Do you deliver?", answer: null, is_ready: false };
    expect(newFaqSuggestions(["is there  parking?"], [parking, delivery])).toEqual([delivery]);
  });

  it("offer customers' unanswered questions once", () => {
    const gaps = [
      { kind: "unanswered_question" as const, unanswered_question: "Do you have Wi-Fi?" },
      { kind: "unanswered_question" as const, unanswered_question: "do you have wi-fi?" },
      { kind: "unanswered_question" as const, unanswered_question: "Is there parking?" },
      { kind: "no_faq" as const, unanswered_question: null },
    ];
    expect(unansweredQuestions(gaps, ["Is there parking?"])).toEqual(["Do you have Wi-Fi?"]);
  });
});
