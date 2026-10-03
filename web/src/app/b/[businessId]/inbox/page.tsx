import { pageMetadata } from "@/components/business/pageMetadata";

import { NoConversationSelected } from "./_components/conversation/NoConversationSelected";

export const generateMetadata = pageMetadata("inbox");

/** The list (in the layout); on wide screens a hint fills the conversation column. */
export default function InboxPage() {
  return <NoConversationSelected />;
}
