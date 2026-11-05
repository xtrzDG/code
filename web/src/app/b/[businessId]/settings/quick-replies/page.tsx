import { pageMetadata } from "@/components/business/pageMetadata";

import { QuickRepliesTab } from "../_components/QuickRepliesTab";

export const generateMetadata = pageMetadata("settings/quick-replies");

/** Settings → Quick replies: the replies the team inserts with "/" in a conversation. */
export default function SettingsQuickRepliesPage() {
  return <QuickRepliesTab />;
}
