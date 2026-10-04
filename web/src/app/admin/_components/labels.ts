import type { Schema } from "@/api/types";
import type { MessageKey } from "@/i18n/translate";

import type { ClientHealthIssue, ClientHealthStatus, ClientSort } from "../_lib/clients";

export const HEALTH_LABELS: Record<ClientHealthStatus, MessageKey> = {
  healthy: "admin.health.healthy",
  attention: "admin.health.attention",
  critical: "admin.health.critical",
};

export const ISSUE_LABELS: Record<ClientHealthIssue, MessageKey> = {
  no_subscription: "admin.issues.no_subscription",
  first_payment_pending: "admin.serverList.firstPaymentPending",
  payment_past_due: "admin.issues.payment_past_due",
  subscription_cancelled: "admin.issues.subscription_cancelled",
  leads_only_mode: "admin.issues.leads_only_mode",
  not_published: "admin.issues.not_published",
  autotests_failed: "admin.issues.autotests_failed",
  tool_errors: "admin.issues.tool_errors",
  many_handoffs: "admin.issues.many_handoffs",
  open_questions: "admin.issues.open_questions",
  package_exceeded: "admin.issues.package_exceeded",
  negative_margin: "admin.issues.negative_margin",
  slow_replies: "adminReplySpeed.issueLabel",
  guard_spike: "adminReplyGuard.issueLabel",
};

export const SORT_LABELS: Record<ClientSort, MessageKey> = {
  health: "admin.sorts.health",
  name: "admin.sorts.name",
  usage: "admin.sorts.usage",
  margin: "admin.sorts.margin",
  cost: "admin.sorts.cost",
  revenue: "admin.sorts.revenue",
};

export const PLAN_LABELS: Record<Schema<"PlanKey">, MessageKey> = {
  chat: "workspace.plans.chat",
  voice_and_chat: "workspace.plans.voice_and_chat",
  plus: "workspace.plans.plus",
};

export const SUBSCRIPTION_LABELS: Record<Schema<"SubscriptionStatus">, MessageKey> = {
  incomplete: "billing.subscribe.statusIncomplete",
  trialing: "billing.status.trialing",
  active: "billing.status.active",
  past_due: "billing.status.past_due",
  cancelled: "billing.status.cancelled",
};

export const BUSINESS_STATUS_LABELS: Record<Schema<"BusinessStatus">, MessageKey> = {
  onboarding: "businesses.status.onboarding",
  testing: "businesses.status.testing",
  live: "businesses.status.live",
  paused: "businesses.status.paused",
};

export const USAGE_KIND_LABELS: Record<Schema<"UsageKind">, MessageKey> = {
  voice_seconds: "admin.detail.usageKinds.voice_seconds",
  llm_input_tokens: "admin.detail.usageKinds.llm_input_tokens",
  llm_output_tokens: "admin.detail.usageKinds.llm_output_tokens",
  dialog: "admin.detail.usageKinds.dialog",
  whatsapp_reply: "admin.detail.usageKinds.whatsapp_reply",
  whatsapp_template: "admin.detail.usageKinds.whatsapp_template",
  transfer_seconds: "admin.detail.usageKinds.transfer_seconds",
  transcription_seconds: "admin.detail.usageKinds.transcription_seconds",
};

export const OUTCOME_LABELS: Record<Schema<"AutotestOutcome">, MessageKey> = {
  passed: "admin.detail.outcomes.passed",
  failed: "admin.detail.outcomes.failed",
  errored: "admin.detail.outcomes.errored",
};

export const SCENARIO_LABELS: Record<Schema<"AutotestScenarioKind">, MessageKey> = {
  booking: "admin.detail.scenarioKinds.booking",
  booking_out_of_hours: "admin.detail.scenarioKinds.booking_out_of_hours",
  cancellation: "admin.detail.scenarioKinds.cancellation",
  price_question: "admin.detail.scenarioKinds.price_question",
  unknown_question: "admin.detail.scenarioKinds.unknown_question",
  discount_request: "admin.detail.scenarioKinds.discount_request",
  rude_customer: "admin.detail.scenarioKinds.rude_customer",
  human_request: "admin.detail.scenarioKinds.human_request",
  prompt_injection: "admin.detail.scenarioKinds.prompt_injection",
  emergency: "admin.detail.scenarioKinds.emergency",
  foreign_language: "admin.detail.scenarioKinds.foreign_language",
  transliterated: "admin.detail.scenarioKinds.transliterated",
  owner_check: "admin.detail.scenarioKinds.owner_check",
};

export const PAYMENT_STATUS_LABELS: Record<Schema<"PaymentStatus">, MessageKey> = {
  created: "admin.detail.paymentStatus.created",
  processing: "admin.detail.paymentStatus.processing",
  approved: "admin.detail.paymentStatus.approved",
  declined: "admin.detail.paymentStatus.declined",
  expired: "admin.detail.paymentStatus.expired",
  reversed: "admin.detail.paymentStatus.reversed",
};

export const INVOICE_STATUS_LABELS: Record<Schema<"InvoiceStatus">, MessageKey> = {
  issued: "billing.invoices.status.issued",
  paid: "billing.invoices.status.paid",
  failed: "billing.invoices.status.failed",
  void: "billing.invoices.status.void",
};

export const INVOICE_KIND_LABELS: Record<Schema<"InvoiceKind">, MessageKey> = {
  service_period: "billing.invoices.kinds.service_period",
  setup_fee: "billing.invoices.kinds.setup_fee",
  usage_overage: "billing.invoices.kinds.usage_overage",
};

export const RATE_SOURCE_LABELS: Record<Schema<"ExchangeRateSource">, MessageKey> = {
  nbg: "admin.detail.rateSources.nbg",
  ecb: "admin.detail.rateSources.ecb",
  planning: "admin.detail.rateSources.planning",
};

export const CHECK_CODE_LABELS: Record<Schema<"AutotestCheckCode">, MessageKey> = {
  no_booking_created: "admin.detail.checkCodes.no_booking_created",
  not_handed_off: "admin.detail.checkCodes.not_handed_off",
  unexpected_records: "admin.detail.checkCodes.unexpected_records",
  wrong_reply_language: "admin.detail.checkCodes.wrong_reply_language",
  wrong_disclosure_language: "admin.detail.checkCodes.wrong_disclosure_language",
  conversation_failed: "admin.detail.checkCodes.conversation_failed",
  no_customer_message: "admin.detail.checkCodes.no_customer_message",
  judge_unavailable: "admin.detail.checkCodes.judge_unavailable",
  judge_unreadable: "admin.detail.checkCodes.judge_unreadable",
  expected_text_missing: "admin.detail.checkCodes.expected_text_missing",
  forbidden_text_mentioned: "admin.detail.checkCodes.forbidden_text_mentioned",
  no_lead_created: "admin.detail.checkCodes.no_lead_created",
};

export const CRITERION_LABELS: Record<Schema<"JudgeCriterion">, MessageKey> = {
  facts_and_prices: "assistant.autotests.criteria.facts_and_prices",
  booking_data: "assistant.autotests.criteria.booking_data",
  ai_disclosure: "assistant.autotests.criteria.ai_disclosure",
  handoff: "assistant.autotests.criteria.handoff",
  language: "assistant.autotests.criteria.language",
};
