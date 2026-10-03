/** API types of the team inbox (aliases of the generated schema, see src/api/types.ts). */

import type { RequestBody, Schema } from "@/api/types";

export type InboxPage = Schema<"InboxPage">;
export type InboxItemView = Schema<"InboxItemView">;
export type InboxViewCounts = Schema<"InboxViewCounts">;
export type InboxHandoffSummary = Schema<"InboxHandoffSummary">;
export type InboxRequestSummary = Schema<"InboxRequestSummary">;
export type InboxAssigneeView = Schema<"InboxAssigneeView">;
export type ConversationAssignmentView = Schema<"ConversationAssignmentView">;

export type ConversationNoteView = Schema<"ConversationNoteView">;
export type ConversationNotePage = Schema<"ConversationNotePage">;

export type QuickReplyView = Schema<"QuickReplyView">;
export type QuickReplyVariable = Schema<"QuickReplyVariable">;
export type FilledQuickReplyView = Schema<"FilledQuickReplyView">;

export type QuickReplyBody = RequestBody<"/v1/businesses/{business_id}/quick-replies", "post">;
