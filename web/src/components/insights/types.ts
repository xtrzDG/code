/**
 * API types of the dashboard, conversations, bookings, leads and handoffs
 * sections (aliases of the generated schema, see src/api/types.ts).
 */

import type { Schema } from "@/api/types";

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

/**
 * Bodies the backend reads itself (operations_routes.py `json_body_reader`),
 * so openapi.json has no request body for them. They mirror
 * app/schemas/dto/operations.py.
 */
export interface ManualBookingBody {
  contact_name: string;
  contact_phone_number?: string | null;
  resource_id?: string | null;
  date: string;
  time?: string | null;
  nights?: number | null;
  party_size: number;
  notes?: string | null;
  source_channel?: ChannelKind;
  language?: string | null;
}

export interface RescheduleBookingBody {
  new_date: string;
  new_time?: string | null;
}

export interface BookingStatusBody {
  status: BookingStatus;
}

export interface LeadStatusBody {
  status: LeadStatus;
}
