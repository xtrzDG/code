import { describe, expect, it } from "vitest";

import type { CallView } from "@/components/insights/types";

import { pickCallSummary } from "./callSummary";

function call(summaries: CallView["summaries"]): CallView {
  return { id: "call_1", started_at: 0, duration_seconds: 42, summaries };
}

describe("the summary on a call card", () => {
  const summaries = [
    { language: "ka", text: "სტუმარს მაგიდა სურს." },
    { language: "ru", text: "Гость хочет столик." },
    { language: "pt-BR", text: "Quer uma mesa." },
  ];

  it("is the one in the reader's language", () => {
    expect(pickCallSummary(call(summaries), "ru")?.text).toBe("Гость хочет столик.");
  });

  it("falls back to the base language, then to the first summary", () => {
    expect(pickCallSummary(call(summaries), "pt")?.text).toBe("Quer uma mesa.");
    expect(pickCallSummary(call(summaries), "en")?.text).toBe("სტუმარს მაგიდა სურს.");
  });

  it("is missing for a call without one", () => {
    expect(pickCallSummary(call([]), "en")).toBeNull();
    expect(pickCallSummary(call(undefined), "en")).toBeNull();
  });
});
