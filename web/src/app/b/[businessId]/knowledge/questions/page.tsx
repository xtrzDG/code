import { subPageMetadata } from "@/components/content/metadata";

import { UnansweredQuestionsScreen } from "./UnansweredQuestionsScreen";

export const generateMetadata = subPageMetadata("knowledge", "knowledge.tabs.questions");

/** Questions customers asked that the assistant could not answer. */
export default function UnansweredQuestionsPage() {
  return <UnansweredQuestionsScreen />;
}
