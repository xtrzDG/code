import type { MessageKey } from "@/i18n/translate";
import type { AutotestScenarioKind } from "@/lib/assistant/autotests";

/** The name of each autotest scenario kind. */
export const SCENARIO_KIND_LABELS: Record<AutotestScenarioKind, MessageKey> = {
  booking: "assistant.autotests.kinds.booking",
  booking_out_of_hours: "assistant.autotests.kinds.booking_out_of_hours",
  cancellation: "assistant.autotests.kinds.cancellation",
  price_question: "assistant.autotests.kinds.price_question",
  unknown_question: "assistant.autotests.kinds.unknown_question",
  discount_request: "assistant.autotests.kinds.discount_request",
  rude_customer: "assistant.autotests.kinds.rude_customer",
  human_request: "assistant.autotests.kinds.human_request",
  prompt_injection: "assistant.autotests.kinds.prompt_injection",
  emergency: "assistant.autotests.kinds.emergency",
  foreign_language: "assistant.autotests.kinds.foreign_language",
  transliterated: "assistant.autotests.kinds.transliterated",
  owner_check: "assistant.autotests.kinds.owner_check",
  prompt_injection_spoof: "assistant.autotests.kinds.prompt_injection_spoof",
  data_exfiltration: "assistant.autotests.kinds.data_exfiltration",
  staff_impersonation: "assistant.autotests.kinds.staff_impersonation",
  tool_abuse: "assistant.autotests.kinds.tool_abuse",
};
