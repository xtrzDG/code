import { pageMetadata } from "@/components/business/pageMetadata";

import { ResourcesScreen } from "./ResourcesScreen";

export const generateMetadata = pageMetadata("assistant/knowledge", "knowledge.tabs.resources");

/** Bookable resources (tables, rooms, masters…) and holidays or special-hours days. */
export default function ResourcesPage() {
  return <ResourcesScreen />;
}
