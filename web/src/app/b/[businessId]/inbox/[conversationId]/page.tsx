import { pageMetadata } from "@/components/business/pageMetadata";

import { ConversationView } from "../_components/conversation/ConversationView";

export const generateMetadata = pageMetadata("inbox");

/** One conversation, next to the list on wide screens and on its own on phones. */
export default async function ConversationPage({ params }: PageProps<"/b/[businessId]/inbox/[conversationId]">) {
  const { conversationId } = await params;
  return <ConversationView conversationId={conversationId} />;
}
