import { pageMetadata } from "@/components/business/pageMetadata";

import { VersionsScreen } from "./VersionsScreen";

export const generateMetadata = pageMetadata("assistant/versions");

/** The assistant's version history. */
export default function VersionsPage() {
  return <VersionsScreen />;
}
