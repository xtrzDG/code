import { sectionMetadata } from "@/components/business/SectionPlaceholder";

import { ConversationDetail } from "../_components/ConversationDetail";

export const generateMetadata = sectionMetadata("conversations");

/** One conversation, next to the feed on wide screens and on its own on phones. */
export default async function ConversationPage({
  params,
}: PageProps<"/b/[businessId]/conversations/[conversationId]">) {
  const { conversationId } = await params;
  return <ConversationDetail conversationId={conversationId} />;
}
