import { pageMetadata } from "@/components/business/pageMetadata";

import { KnowledgeItemsScreen } from "./KnowledgeItemsScreen";

export const generateMetadata = pageMetadata("assistant/knowledge");

/** Knowledge: menu, services, prices, questions and rules the assistant answers from. */
export default function KnowledgePage() {
  return <KnowledgeItemsScreen />;
}
