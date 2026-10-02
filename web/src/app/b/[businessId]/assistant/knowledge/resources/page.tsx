import { subPageMetadata } from "@/components/content/metadata";

import { ResourcesScreen } from "./ResourcesScreen";

export const generateMetadata = subPageMetadata("knowledge", "knowledge.tabs.resources");

/** Bookable resources (tables, rooms, masters…) and holidays or special-hours days. */
export default function ResourcesPage() {
  return <ResourcesScreen />;
}
