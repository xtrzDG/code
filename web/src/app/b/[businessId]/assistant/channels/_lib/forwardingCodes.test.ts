import { describe, expect, it } from "vitest";

import type { Schema } from "@/api/types";
import { en } from "@/i18n/messages/en";
import { it as italian } from "@/i18n/messages/it";
import { createTranslator } from "@/i18n/translate";

import { dialHref, sortStarCodes } from "./channels";
import { forwardingCodeRows } from "./forwardingCodes";

/** Verizon's star codes for +1 212-555-0123, as the API answers them (cancel first, to be sorted). */
const VERIZON: Schema<"CallForwardingStarCode">[] = [
  { condition: "cancel_all", dial_code: "*73", description: "Switch call forwarding off." },
  {
    condition: "no_answer_or_busy",
    dial_code: "*712125550123",
    description: "Forward calls you do not answer and calls while the line is busy (one code for both).",
  },
];
const T_MOBILE: Schema<"CallForwardingCode">[] = [
  { condition: "cancel_all", dial_code: "##004#", description: "Switch forwarding off." },
  { condition: "busy", dial_code: "**67*12125550123#", description: "Busy calls." },
  { condition: "no_answer", dial_code: "**61*12125550123#", description: "Unanswered calls." },
  { condition: "unreachable", dial_code: "**62*12125550123#", description: "Calls while off or out of coverage." },
];

describe("star codes", () => {
  it("come forwarding first, then switching off", () => {
    expect(sortStarCodes(VERIZON).map((code) => code.dial_code)).toEqual(["*712125550123", "*73"]);
  });

  it("open the dialer as they are: a star code has no # to escape", () => {
    expect(dialHref("*712125550123")).toBe("tel:*712125550123");
    expect(dialHref("*73")).toBe("tel:*73");
    expect(dialHref("##004#")).toBe("tel:%23%23004%23");
  });
});

describe("the rows of a carrier's codes", () => {
  it("list a carrier with star codes only (Verizon) by its star codes", () => {
    expect(forwardingCodeRows([], VERIZON)).toEqual([
      {
        key: "star-no_answer_or_busy",
        label: "channels.forwarding.starCondition.no_answer_or_busy",
        description: VERIZON[1]!.description,
        dialCode: "*712125550123",
      },
      { key: "star-cancel_all", label: "channels.forwarding.starCondition.cancel_all", description: "Switch call forwarding off.", dialCode: "*73" },
    ]);
  });

  it("list GSM codes in their usual order, then star codes, each key once", () => {
    const rows = forwardingCodeRows(T_MOBILE, VERIZON);

    expect(rows.map((row) => row.dialCode)).toEqual([
      "**61*12125550123#",
      "**67*12125550123#",
      "**62*12125550123#",
      "##004#",
      "*712125550123",
      "*73",
    ]);
    expect(rows[0]!.label).toBe("channels.forwarding.condition.no_answer");
    expect(new Set(rows.map((row) => row.key)).size).toBe(rows.length);
  });

  it("take an API without star codes (a carrier of the release before) as none", () => {
    expect(forwardingCodeRows(T_MOBILE).map((row) => row.key)).toEqual(["gsm-no_answer", "gsm-busy", "gsm-unreachable", "gsm-cancel_all"]);
    expect(forwardingCodeRows([], undefined)).toEqual([]);
  });

  it("name every star code in English and Italian", () => {
    for (const [locale, messages] of [["en", en], ["it", italian]] as const) {
      const { t } = createTranslator(locale, messages);
      for (const row of forwardingCodeRows([], VERIZON)) {
        expect(t(row.label), `${locale} ${row.label}`).not.toBe(row.label);
      }
    }
  });
});
