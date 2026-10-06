/**
 * Texts and badge tones of the API enums shown in the dashboard,
 * conversations, bookings, leads and handoffs sections.
 */

import type { BadgeTone } from "@/components/ui";
import type { MessageKey } from "@/i18n/translate";

import type {
  AssistantToolName,
  BookingStatus,
  ChannelKind,
  ConversationStatus,
  HandoffReason,
  HandoffStatus,
  HandoffUrgency,
  LeadStatus,
  LeadType,
  MessageAuthor,
} from "./types";

export interface StatusLabel {
  label: MessageKey;
  tone: BadgeTone;
}

export const CHANNEL_LABELS: Record<ChannelKind, MessageKey> = {
  phone: "insights.channels.phone",
  whatsapp: "insights.channels.whatsapp",
  instagram: "insights.channels.instagram",
  messenger: "insights.channels.messenger",
  telegram: "insights.channels.telegram",
  web_chat: "insights.channels.web_chat",
  viber: "insights.channels.viber",
  owner_test: "insights.channels.owner_test",
};

/** Channels a customer can reach the business through (not the owner's test chat). */
export const CUSTOMER_CHANNELS: readonly ChannelKind[] = [
  "phone",
  "whatsapp",
  "telegram",
  "instagram",
  "messenger",
  "viber",
  "web_chat",
];

export const CONVERSATION_STATUS: Record<ConversationStatus, StatusLabel> = {
  open: { label: "conversations.status.open", tone: "info" },
  handoff: { label: "conversations.status.handoff", tone: "warning" },
  closed: { label: "conversations.status.closed", tone: "neutral" },
};

export const MESSAGE_AUTHORS: Record<MessageAuthor, MessageKey> = {
  customer: "conversations.author.customer",
  assistant: "conversations.author.assistant",
  staff: "conversations.author.staff",
  system: "conversations.author.system",
};

export const TOOL_LABELS: Record<AssistantToolName, MessageKey> = {
  search_knowledge: "conversations.tools.search_knowledge",
  get_price: "conversations.tools.get_price",
  check_availability: "conversations.tools.check_availability",
  create_booking: "conversations.tools.create_booking",
  cancel_booking: "conversations.tools.cancel_booking",
  reschedule_booking: "conversations.tools.reschedule_booking",
  list_my_bookings: "conversations.tools.list_my_bookings",
  join_waitlist: "conversations.tools.join_waitlist",
  create_lead: "conversations.tools.create_lead",
  handoff_to_human: "conversations.tools.handoff_to_human",
  send_link: "conversations.tools.send_link",
  record_unanswered_question: "conversations.tools.record_unanswered_question",
};

export const BOOKING_STATUS: Record<BookingStatus, StatusLabel> = {
  pending: { label: "bookings.status.pending", tone: "warning" },
  confirmed: { label: "bookings.status.confirmed", tone: "success" },
  completed: { label: "bookings.status.completed", tone: "neutral" },
  no_show: { label: "bookings.status.no_show", tone: "danger" },
  cancelled: { label: "bookings.status.cancelled", tone: "neutral" },
};

export const BOOKING_STATUSES: readonly BookingStatus[] = ["pending", "confirmed", "completed", "no_show", "cancelled"];

export const LEAD_STATUS: Record<LeadStatus, StatusLabel> = {
  new: { label: "leads.status.new", tone: "accent" },
  in_progress: { label: "leads.status.in_progress", tone: "info" },
  won: { label: "leads.status.won", tone: "success" },
  lost: { label: "leads.status.lost", tone: "neutral" },
};

export const LEAD_STATUSES: readonly LeadStatus[] = ["new", "in_progress", "won", "lost"];

export const LEAD_TYPES: Record<LeadType, MessageKey> = {
  banquet: "leads.type.banquet",
  group: "leads.type.group",
  corporate: "leads.type.corporate",
  order: "leads.type.order",
  viewing: "leads.type.viewing",
  other: "leads.type.otherRequest",
};

export const HANDOFF_REASONS: Record<HandoffReason, MessageKey> = {
  customer_request: "handoffs.reason.customer_request",
  complaint: "handoffs.reason.complaint",
  vip_guest: "handoffs.reason.vip_guest",
  non_standard_request: "handoffs.reason.non_standard_request",
  unknown_answer: "handoffs.reason.unknown_answer",
  emergency: "handoffs.reason.emergency",
  sensitive_topic: "handoffs.reason.sensitive_topic",
  profile_rule: "handoffs.reason.profile_rule",
  unverified_numbers: "handoffs.reason.unverified_numbers",
};

export const HANDOFF_URGENCY: Record<HandoffUrgency, StatusLabel> = {
  critical: { label: "handoffs.urgency.critical", tone: "danger" },
  high: { label: "handoffs.urgency.high", tone: "warning" },
  normal: { label: "handoffs.urgency.normal", tone: "info" },
  low: { label: "handoffs.urgency.low", tone: "neutral" },
};

export const HANDOFF_STATUS: Record<HandoffStatus, StatusLabel> = {
  pending: { label: "handoffs.status.pending", tone: "warning" },
  notified: { label: "handoffs.status.notified", tone: "info" },
  notification_failed: { label: "handoffs.status.notification_failed", tone: "danger" },
  resolved: { label: "handoffs.status.resolved", tone: "success" },
};

/** Every message key used by the maps above (checked against the dictionaries in tests). */
export function allLabelKeys(): MessageKey[] {
  const statusKeys = (map: Record<string, StatusLabel>) => Object.values(map).map((entry) => entry.label);
  return [
    ...Object.values(CHANNEL_LABELS),
    ...statusKeys(CONVERSATION_STATUS),
    ...Object.values(MESSAGE_AUTHORS),
    ...Object.values(TOOL_LABELS),
    ...statusKeys(BOOKING_STATUS),
    ...statusKeys(LEAD_STATUS),
    ...Object.values(LEAD_TYPES),
    ...Object.values(HANDOFF_REASONS),
    ...statusKeys(HANDOFF_URGENCY),
    ...statusKeys(HANDOFF_STATUS),
  ];
}
