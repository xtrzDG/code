import { pageMetadata } from "@/components/business/pageMetadata";

import { VersionDetailScreen } from "./VersionDetailScreen";

export const generateMetadata = pageMetadata("assistant/versions", "assistant.detail.title");

/** One assistant version: autotests, facts, instruction, publishing and rollback. */
export default async function VersionPage({ params }: PageProps<"/b/[businessId]/assistant/versions/[versionId]">) {
  const { versionId } = await params;
  return <VersionDetailScreen key={versionId} versionId={versionId} />;
}
