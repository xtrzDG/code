import { pageMetadata } from "@/components/business/pageMetadata";

import { ConversationDetail } from "../_components/ConversationDetail";

export const generateMetadata = pageMetadata("messages");

/** One conversation, next to the feed on wide screens and on its own on phones. */
export default async function ConversationPage({
  params,
}: PageProps<"/b/[businessId]/conversations/[conversationId]">) {
  const { conversationId } = await params;
  return <ConversationDetail conversationId={conversationId} />;
}
