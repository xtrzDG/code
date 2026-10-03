import { describe, expect, it } from "vitest";

import { en } from "@/i18n/messages/en";
import { ka } from "@/i18n/messages/ka";
import { ru } from "@/i18n/messages/ru";
import { createTranslator } from "@/i18n/translate";

import {
  callSettingsBody,
  callSettingsForm,
  isSameCallSettings,
  MISSED_CALL_REASON_LABELS,
  READINESS_TEXTS,
  SKIP_REASON_LABELS,
  templateNameError,
  TEXT_BACK_CHANNEL_LABELS,
  TEXT_BACK_STATUS_LABELS,
  textBackReadiness,
  type CallSettingsView,
} from "./calls";

const VIEW: CallSettingsView = {
  is_summary_enabled: true,
  is_text_back_enabled: false,
  text_back_template_name: null,
  is_sms_fallback_enabled: true,
  is_whatsapp_connected: false,
  is_sms_available: true,
  template_previews: [],
};

describe("the call settings form", () => {
  it("starts from the stored settings and saves a trimmed name", () => {
    const form = callSettingsForm({ ...VIEW, text_back_template_name: "missed_call" });

    expect(form).toEqual({
      isSummaryEnabled: true,
      isTextBackEnabled: false,
      templateName: "missed_call",
      isSmsFallbackEnabled: true,
    });
    expect(callSettingsBody({ ...form, templateName: "  missed_call_v2 " }).text_back_template_name).toBe("missed_call_v2");
    expect(callSettingsBody({ ...form, templateName: "   " }).text_back_template_name).toBeNull();
  });

  it("knows when nothing changed", () => {
    const form = callSettingsForm(VIEW);

    expect(isSameCallSettings(form, VIEW)).toBe(true);
    expect(isSameCallSettings({ ...form, templateName: " " }, VIEW)).toBe(true);
    expect(isSameCallSettings({ ...form, isTextBackEnabled: true }, VIEW)).toBe(false);
    expect(isSameCallSettings({ ...form, templateName: "missed_call" }, VIEW)).toBe(false);
  });

  it("accepts only names Meta accepts", () => {
    const form = callSettingsForm(VIEW);

    expect(templateNameError({ ...form, templateName: "" })).toBeNull();
    expect(templateNameError({ ...form, templateName: "missed_call_2" })).toBeNull();
    expect(templateNameError({ ...form, templateName: "Missed call" })).toBe("callSettings.textBack.templateInvalid");
  });
});

describe("what a missed caller gets", () => {
  const on = { ...callSettingsForm(VIEW), isTextBackEnabled: true };

  it("is nothing while text-backs are off", () => {
    expect(textBackReadiness(callSettingsForm(VIEW), VIEW)).toBe("off");
  });

  it("is the WhatsApp template with a connected number and a name", () => {
    const connected = { ...VIEW, is_whatsapp_connected: true };

    expect(textBackReadiness({ ...on, templateName: "missed_call" }, connected)).toBe("whatsapp");
    expect(textBackReadiness(on, connected)).toBe("sms");
  });

  it("is an SMS only when allowed and set up", () => {
    expect(textBackReadiness(on, VIEW)).toBe("sms");
    expect(textBackReadiness({ ...on, isSmsFallbackEnabled: false }, VIEW)).toBe("none");
    expect(textBackReadiness(on, { ...VIEW, is_sms_available: false })).toBe("none");
  });
});

describe("the labels", () => {
  it("exist in every language", () => {
    const keys = [
      ...Object.values(READINESS_TEXTS),
      ...Object.values(TEXT_BACK_STATUS_LABELS),
      ...Object.values(TEXT_BACK_CHANNEL_LABELS),
      ...Object.values(MISSED_CALL_REASON_LABELS),
      ...Object.values(SKIP_REASON_LABELS),
    ];
    for (const [locale, messages] of [
      ["en", en],
      ["ru", ru],
      ["ka", ka],
    ] as const) {
      const { t } = createTranslator(locale, messages);
      for (const key of keys) {
        expect(t(key), `${locale} ${key}`).not.toBe(key);
      }
    }
  });
});
