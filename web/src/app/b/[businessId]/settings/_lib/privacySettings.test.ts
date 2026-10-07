import { describe, expect, it } from "vitest";

import { en } from "@/i18n/messages/en";
import { ka } from "@/i18n/messages/ka";
import { ru } from "@/i18n/messages/ru";
import { createTranslator } from "@/i18n/translate";
import { daysLabel, periodLabel, periodParts } from "@/lib/retentionPeriods";

import {
  CONVERSATION_PERIODS,
  isSameRetention,
  MODEL_RECORD_PERIODS,
  NAMED_PROCESSORS,
  periodChoices,
  PURGE_COUNT_FIELDS,
  purgeSummary,
  retentionBody,
  retentionForm,
  shorterPeriods,
  type PrivacySettingsView,
  type RetentionPurgeCounts,
} from "./privacySettings";

const VIEW: PrivacySettingsView = {
  conversation_retention_days: 730,
  llm_turn_retention_days: 30,
  recording_retention_days: 90,
  last_purge: null,
  erasure_processors: ["langfuse", "elevenlabs"],
  quality_sampling_allowed: true,
};

const NO_COUNTS: RetentionPurgeCounts = {
  deleted_messages: 0,
  deleted_llm_turns: 0,
  deleted_notes: 0,
  deleted_media: 0,
  deleted_missed_calls: 0,
  erased_calls: 0,
  anonymized_leads: 0,
  anonymized_bookings: 0,
  anonymized_handoffs: 0,
};

describe("the retention form", () => {
  it("starts from the stored settings and saves them as the API reads them", () => {
    const form = retentionForm(VIEW);

    expect(form).toEqual({ conversationDays: 730, modelRecordDays: 30, isQualitySamplingAllowed: true });
    expect(retentionBody({ conversationDays: 365, modelRecordDays: 14, isQualitySamplingAllowed: false })).toEqual({
      conversation_retention_days: 365,
      llm_turn_retention_days: 14,
      quality_sampling_allowed: false,
    });
    expect(isSameRetention(form, VIEW)).toBe(true);
    expect(isSameRetention({ ...form, modelRecordDays: 14 }, VIEW)).toBe(false);
    expect(isSameRetention({ ...form, isQualitySamplingAllowed: false }, VIEW)).toBe(false);
  });

  it("asks before a shorter period, which deletes data tonight, not before a longer one", () => {
    const form = retentionForm(VIEW);
    expect(shorterPeriods({ ...form, conversationDays: 365 }, VIEW)).toEqual(["conversationDays"]);
    expect(shorterPeriods({ ...form, conversationDays: 365, modelRecordDays: 7 }, VIEW)).toEqual([
      "conversationDays",
      "modelRecordDays",
    ]);
    expect(shorterPeriods({ ...form, conversationDays: 1825, isQualitySamplingAllowed: false }, VIEW)).toEqual([]);
  });

  it("offers the presets within the API's bounds and keeps a stored value set some other way", () => {
    expect(Math.min(...CONVERSATION_PERIODS)).toBe(30);
    expect(Math.max(...MODEL_RECORD_PERIODS)).toBe(30);
    expect(periodChoices(CONVERSATION_PERIODS, 400)).toEqual([30, 90, 180, 365, 400, 730, 1095, 1825]);
    expect(periodChoices(MODEL_RECORD_PERIODS, 30)).toEqual([7, 14, 30]);
  });
});

describe("periods as people say them", () => {
  it("picks whole years, then whole months, else days", () => {
    expect(periodParts(730)).toEqual({ unit: "years", count: 2 });
    expect(periodParts(90)).toEqual({ unit: "months", count: 3 });
    expect(periodParts(30)).toEqual({ unit: "months", count: 1 });
    expect(periodParts(14)).toEqual({ unit: "days", count: 14 });
    expect(periodParts(400)).toEqual({ unit: "days", count: 400 });
  });

  it("names them in every language of the cabinet", () => {
    expect(periodLabel(createTranslator("en", en).tp, 730)).toBe("2 years");
    expect(periodLabel(createTranslator("ru", ru).tp, 730)).toBe("2 года");
    expect(periodLabel(createTranslator("ru", ru).tp, 1825)).toBe("5 лет");
    expect(periodLabel(createTranslator("ka", ka).tp, 90)).toBe("3 თვე");
    expect(daysLabel(createTranslator("ru", ru).tp, 30)).toBe("30 дней");
    expect(daysLabel(createTranslator("en", en).tp, 1)).toBe("1 day");
  });
});

describe("the latest cleanup", () => {
  it("adds up what it removed and lists only the kinds it touched, in order", () => {
    const summary = purgeSummary({ ...NO_COUNTS, deleted_messages: 1204, anonymized_leads: 3, deleted_llm_turns: 40 });

    expect(summary.total).toBe(1247);
    expect(summary.parts.map((part) => part.field)).toEqual(["deleted_messages", "deleted_llm_turns", "anonymized_leads"]);
    expect(purgeSummary(NO_COUNTS)).toEqual({ total: 0, parts: [] });
  });

  it("has a label for every count and every named sub-processor in en, ru and ka", () => {
    for (const messages of [en, ru, ka]) {
      for (const field of PURGE_COUNT_FIELDS) {
        expect(messages.privacyRetention.counts[field]).toBeTruthy();
      }
      for (const processor of NAMED_PROCESSORS) {
        expect(messages.privacyRetention.processors[processor]).toBeTruthy();
      }
    }
  });
});
