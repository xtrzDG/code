import { subPageMetadata } from "@/components/content/metadata";

import { VersionDetailScreen } from "./VersionDetailScreen";

export const generateMetadata = subPageMetadata("assistant", "assistant.detail.title");

/** One assistant version: autotests, facts, instruction, publishing and rollback. */
export default async function VersionPage({ params }: PageProps<"/b/[businessId]/assistant/versions/[versionId]">) {
  const { versionId } = await params;
  return <VersionDetailScreen key={versionId} versionId={versionId} />;
}
