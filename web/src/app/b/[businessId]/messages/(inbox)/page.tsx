import { sectionMetadata } from "@/components/business/SectionPlaceholder";

import { NoConversationSelected } from "./_components/NoConversationSelected";

export const generateMetadata = sectionMetadata("conversations");

/** The feed (in the layout); on wide screens a hint fills the card column. */
export default function ConversationsPage() {
  return <NoConversationSelected />;
}
