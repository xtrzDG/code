import { pageMetadata } from "@/components/business/pageMetadata";

import { VersionDetailScreen } from "./VersionDetailScreen";

export const generateMetadata = pageMetadata("assistant/versions", "assistant.detail.title");

/**
 * One assistant version: autotests, facts, instruction, publishing and
 * rollback. `?checks=problems` (the link of a failed "Apply changes") opens
 * the checks that did not pass.
 */
export default async function VersionPage({ params, searchParams }: PageProps<"/b/[businessId]/assistant/versions/[versionId]">) {
  const { versionId } = await params;
  const { checks } = await searchParams;
  return <VersionDetailScreen key={versionId} versionId={versionId} showProblems={checks === "problems"} />;
}
