import { pageMetadata } from "@/components/business/pageMetadata";

import { SegmentsScreen } from "./SegmentsScreen";

export const generateMetadata = pageMetadata("customers/segments");

/** Customers → Segments (owners): saved groups of customers and their CSV. */
export default function SegmentsPage() {
  return <SegmentsScreen />;
}
