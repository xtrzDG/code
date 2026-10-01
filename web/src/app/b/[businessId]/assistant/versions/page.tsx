import { subPageMetadata } from "@/components/content/metadata";

import { VersionsScreen } from "./VersionsScreen";

export const generateMetadata = subPageMetadata("assistant", "assistant.tabs.versions");

/** The assistant's version history. */
export default function VersionsPage() {
  return <VersionsScreen />;
}
