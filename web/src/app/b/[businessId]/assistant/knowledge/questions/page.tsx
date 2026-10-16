import { pageMetadata } from "@/components/business/pageMetadata";

import { UnansweredQuestionsScreen } from "./UnansweredQuestionsScreen";

export const generateMetadata = pageMetadata("assistant/knowledge", "knowledge.tabs.questions");

/** Questions customers asked that the assistant could not answer. */
export default function UnansweredQuestionsPage() {
  return <UnansweredQuestionsScreen />;
}
