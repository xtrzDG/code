import { pageMetadata } from "@/components/business/pageMetadata";

import { NoConversationSelected } from "./_components/NoConversationSelected";

export const generateMetadata = pageMetadata("messages");

/** The feed (in the layout); on wide screens a hint fills the card column. */
export default function ConversationsPage() {
  return <NoConversationSelected />;
}
