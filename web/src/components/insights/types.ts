/**
 * API types of the dashboard, conversations, bookings, leads and handoffs
 * sections (aliases of the generated schema, see src/api/types.ts).
 */

import type { RequestBody, Schema } from "@/api/types";

export type DashboardStats = Schema<"DashboardStats">;
export type BillingOverview = Schema<"BillingOverview">;
export type PackageUsageView = Schema<"PackageUsageView">;

export type ChannelKind = Schema<"ChannelKind">;
export type ConversationStatus = Schema<"ConversationStatus">;
export type ConversationSummaryView = Schema<"ConversationSummaryView">;
export type ConversationDetailView = Schema<"ConversationDetailView">;
export type MessageView = Schema<"MessageView">;
export type MessageAuthor = Schema<"MessageAuthor">;
export type ToolCallView = Schema<"ToolCallView">;
export type AssistantToolName = Schema<"AssistantToolName">;

export type BookingView = Schema<"BookingView">;
export type BookingResult = Schema<"BookingResult">;
export type BookingStatus = Schema<"BookingStatus">;
export type BookingUnit = Schema<"BookingUnit">;
export type AvailableSlot = Schema<"AvailableSlot">;
export type AvailabilityResult = Schema<"AvailabilityResult">;
export type ResourceView = Schema<"ResourceView">;

export type LeadListItem = Schema<"LeadListItem">;
export type LeadView = Schema<"LeadView">;
export type LeadStatus = Schema<"LeadStatus">;
export type LeadType = Schema<"LeadType">;

export type HandoffListItem = Schema<"HandoffListItem">;
export type HandoffReason = Schema<"HandoffReason">;
export type HandoffStatus = Schema<"HandoffStatus">;
export type HandoffUrgency = Schema<"HandoffUrgency">;

// Pages of the cabinet lists ({items, next_cursor}).
export type ConversationPage = Schema<"ConversationPage">;
export type BookingPage = Schema<"BookingPage">;
export type LeadPage = Schema<"LeadPage">;
export type HandoffPage = Schema<"HandoffPage">;

export type CallView = Schema<"CallView">;
export type CallOutcome = Schema<"CallOutcome">;
export type ConversationRating = Schema<"ConversationRating">;
export type StaffReplyView = Schema<"StaffReplyView">;
export type StaffReplyBlock = Schema<"StaffReplyBlock">;
export type StaffMessageResult = Schema<"StaffMessageResult">;

export type DashboardDay = Schema<"DashboardDay">;
export type DashboardPackageUsage = Schema<"DashboardPackageUsage">;

// Request bodies (described in openapi.json).
export type ManualBookingBody = RequestBody<"/v1/businesses/{business_id}/bookings", "post">;
export type RescheduleBookingBody = RequestBody<"/v1/businesses/{business_id}/bookings/{booking_id}/reschedule", "post">;
export type BookingUpdateBody = RequestBody<"/v1/businesses/{business_id}/bookings/{booking_id}", "patch">;
export type LeadStatusBody = RequestBody<"/v1/businesses/{business_id}/leads/{lead_id}", "patch">;
export type StaffMessageBody = RequestBody<
  "/v1/businesses/{business_id}/conversations/{conversation_id}/messages",
  "post"
>;
