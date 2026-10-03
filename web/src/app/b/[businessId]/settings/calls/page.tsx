import { pageMetadata } from "@/components/business/pageMetadata";

import { CallsTab } from "../_components/CallsTab";

export const generateMetadata = pageMetadata("settings/calls");

/** Settings → Calls: summaries after calls and messages to callers who did not get through. */
export default function SettingsCallsPage() {
  return <CallsTab />;
}
