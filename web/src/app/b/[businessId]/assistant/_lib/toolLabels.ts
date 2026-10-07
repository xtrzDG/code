import type { MessageKey } from "@/i18n/translate";
import type { AssistantToolName } from "@/lib/assistant/versions";

/** The name and description of each tool the assistant can call. */
export const TOOL_LABELS: Record<AssistantToolName, { name: MessageKey; description: MessageKey }> = {
  search_knowledge: { name: "assistant.tools.search_knowledge.name", description: "assistant.tools.search_knowledge.description" },
  get_price: { name: "assistant.tools.get_price.name", description: "assistant.tools.get_price.description" },
  check_availability: { name: "assistant.tools.check_availability.name", description: "assistant.tools.check_availability.description" },
  create_booking: { name: "assistant.tools.create_booking.name", description: "assistant.tools.create_booking.description" },
  cancel_booking: { name: "assistant.tools.cancel_booking.name", description: "assistant.tools.cancel_booking.description" },
  reschedule_booking: { name: "assistant.tools.reschedule_booking.name", description: "assistant.tools.reschedule_booking.description" },
  list_my_bookings: { name: "assistant.tools.list_my_bookings.name", description: "assistant.tools.list_my_bookings.description" },
  join_waitlist: { name: "assistant.tools.join_waitlist.name", description: "assistant.tools.join_waitlist.description" },
  create_lead: { name: "assistant.tools.create_lead.name", description: "assistant.tools.create_lead.description" },
  handoff_to_human: { name: "assistant.tools.handoff_to_human.name", description: "assistant.tools.handoff_to_human.description" },
  send_link: { name: "assistant.tools.send_link.name", description: "assistant.tools.send_link.description" },
  record_unanswered_question: {
    name: "assistant.tools.record_unanswered_question.name",
    description: "assistant.tools.record_unanswered_question.description",
  },
  offer_choices: { name: "assistant.tools.offer_choices.name", description: "assistant.tools.offer_choices.description" },
};
