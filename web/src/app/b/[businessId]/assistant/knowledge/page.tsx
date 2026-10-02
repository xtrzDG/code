import { sectionMetadata } from "@/components/business/SectionPlaceholder";

import { KnowledgeItemsScreen } from "./KnowledgeItemsScreen";

export const generateMetadata = sectionMetadata("knowledge");

/** Knowledge: menu, services, prices, questions and rules the assistant answers from. */
export default function KnowledgePage() {
  return <KnowledgeItemsScreen />;
}
