import type { Schema } from "@/api/types";
import { privacyNoticeOfChat } from "@/lib/publicSite/customerPageLinks";

/**
 * The business's privacy notice for the foot of its booking page: the one
 * the API names (the business's own, else the default notice of its chat
 * page), else the notice of its chat page when the booking lists it.
 */
export function privacyNoticeOfView(view: Schema<"ManagedBookingView">): string | null {
  if (view.privacy_url) {
    return view.privacy_url;
  }
  const chat = (view.chat_links ?? []).find((link) => link.kind === "hosted_chat");
  return chat ? privacyNoticeOfChat(chat.url) : null;
}
