import { sectionMetadata } from "@/components/business/SectionPlaceholder";

import { TestChatScreen } from "./TestChatScreen";

export const generateMetadata = sectionMetadata("assistant");

/** Assistant: the test chat; `?version=…` talks to a chosen version. */
export default async function AssistantPage({ searchParams }: PageProps<"/b/[businessId]/assistant">) {
  const { version } = await searchParams;
  return <TestChatScreen initialVersionId={typeof version === "string" ? version : null} />;
}
