import { describe, expect, it } from "vitest";

import { en } from "@/i18n/messages/en";
import { it as italian } from "@/i18n/messages/it";
import { createTranslator } from "@/i18n/translate";

import {
  callerNoticeKeys,
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
  TRANSFER_READINESS_TEXTS,
  transferReadiness,
  turnedOffText,
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
  is_recording_enabled: false,
  is_staff_transfer_confirmed: false,
  staff_transfer_confirmed_by: null,
  staff_transfer_confirmed_at: null,
  transfer_phone_number: null,
};

describe("the call settings form", () => {
  it("starts from the stored settings and saves a trimmed name", () => {
    const form = callSettingsForm({ ...VIEW, text_back_template_name: "missed_call" });

    expect(form).toEqual({
      isSummaryEnabled: true,
      isTextBackEnabled: false,
      templateName: "missed_call",
      isSmsFallbackEnabled: true,
      isRecordingEnabled: false,
      isStaffTransferConfirmed: false,
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
    expect(isSameCallSettings({ ...form, isRecordingEnabled: true }, VIEW)).toBe(false);
    expect(isSameCallSettings({ ...form, isStaffTransferConfirmed: true }, VIEW)).toBe(false);
  });

  it("saves the recording switch and the staff notice of transfers", () => {
    const form = callSettingsForm({ ...VIEW, is_recording_enabled: true, is_staff_transfer_confirmed: true });

    expect(form.isRecordingEnabled).toBe(true);
    expect(form.isStaffTransferConfirmed).toBe(true);
    expect(callSettingsBody(form)).toMatchObject({ is_recording_enabled: true, is_staff_transfer_confirmed: true });
    expect(callSettingsBody({ ...form, isRecordingEnabled: false }).is_recording_enabled).toBe(false);
  });

  it("puts callers through only with a staff number and the owner's confirmation", () => {
    const form = callSettingsForm(VIEW);
    const withNumber: CallSettingsView = { ...VIEW, transfer_phone_number: "+393471234567" };

    expect(transferReadiness(form, VIEW)).toBe("noNumber");
    expect(transferReadiness({ ...form, isStaffTransferConfirmed: true }, VIEW)).toBe("noNumber");
    expect(transferReadiness(form, withNumber)).toBe("unconfirmed");
    expect(transferReadiness({ ...form, isStaffTransferConfirmed: true }, withNumber)).toBe("ready");
  });

  it("offers Undo when recording or transfers are switched off", () => {
    const form = { ...callSettingsForm(VIEW), isRecordingEnabled: true, isStaffTransferConfirmed: true };

    expect(turnedOffText(form, { ...form, isRecordingEnabled: false })).toBe("callSettings.recording.turnedOff");
    expect(turnedOffText(form, { ...form, isStaffTransferConfirmed: false })).toBe("callSettings.transfers.turnedOff");
    expect(turnedOffText({ ...form, isRecordingEnabled: false }, form)).toBeNull();
  });

  it("accepts only names Meta accepts", () => {
    const form = callSettingsForm(VIEW);

    expect(templateNameError({ ...form, templateName: "" })).toBeNull();
    expect(templateNameError({ ...form, templateName: "missed_call_2" })).toBeNull();
    expect(templateNameError({ ...form, templateName: "Missed call" })).toBe("callSettings.textBack.templateInvalid");
  });
});

describe("the Undo of a save", () => {
  const on = {
    isSummaryEnabled: true,
    isTextBackEnabled: true,
    templateName: "",
    isSmsFallbackEnabled: true,
    isRecordingEnabled: false,
    isStaffTransferConfirmed: false,
  };

  it("is offered when something was switched off, and names it", () => {
    expect(turnedOffText(on, { ...on, isTextBackEnabled: false })).toBe("callSettings.textBack.turnedOff");
    expect(turnedOffText(on, { ...on, isSmsFallbackEnabled: false })).toBe("callSettings.textBack.smsTurnedOff");
    expect(turnedOffText(on, { ...on, isSummaryEnabled: false })).toBe("callSettings.summaries.turnedOff");
  });

  it("is not offered for switching on or for a new template name", () => {
    expect(turnedOffText({ ...on, isTextBackEnabled: false }, on)).toBeNull();
    expect(turnedOffText(on, { ...on, templateName: "missed_call" })).toBeNull();
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
      ...Object.values(TRANSFER_READINESS_TEXTS),
      "callSettings.recording.turnedOff" as const,
      "callSettings.transfers.turnedOff" as const,
      ...Object.values(TEXT_BACK_STATUS_LABELS),
      ...Object.values(TEXT_BACK_CHANNEL_LABELS),
      ...Object.values(MISSED_CALL_REASON_LABELS),
      ...Object.values(SKIP_REASON_LABELS),
    ];
    for (const [locale, messages] of [
      ["en", en],
      ["it", italian],
    ] as const) {
      const { t } = createTranslator(locale, messages);
      for (const key of keys) {
        expect(t(key), `${locale} ${key}`).not.toBe(key);
      }
    }
  });
});

describe("what callers hear", () => {
  it("says the call is recorded only while recording is on, and where the privacy notice is once, last", () => {
    const { t } = createTranslator("en", en);
    const said = (isRecording: boolean) =>
      callerNoticeKeys(isRecording)
        .map((key) => t(key, { business: "Trattoria Da Mario" }))
        .join(" ");

    // The API's greeting, sentence by sentence (BuildCallGreetingUseCase).
    expect(said(false)).toBe(
      'Hello! This is the AI assistant of Trattoria Da Mario. To talk to a staff member, say "operator". ' +
        "Our privacy notice is on our web page.",
    );
    expect(said(true)).toBe(
      "Hello! This is the AI assistant of Trattoria Da Mario. The call is recorded. " +
        'To talk to a staff member, say "operator". Our privacy notice is on our web page.',
    );
  });

  it("is said in Italian too", () => {
    const { t } = createTranslator("it", italian);

    expect(callerNoticeKeys(false).map((key) => t(key, { business: "Da Mario" }))).toEqual([
      "Buongiorno! Risponde l'assistente IA di Da Mario.",
      "Per parlare con un membro dello staff, dica «operatore».",
      "L'informativa sulla privacy è sulla nostra pagina web.",
    ]);
  });
});
