import { pageMetadata } from "@/components/business/pageMetadata";

import { ChecksScreen } from "./ChecksScreen";

export const generateMetadata = pageMetadata("assistant/checks");

/** Assistant → My checks: the owner's own questions every "Apply changes" asks. */
export default function ChecksPage() {
  return <ChecksScreen />;
}
