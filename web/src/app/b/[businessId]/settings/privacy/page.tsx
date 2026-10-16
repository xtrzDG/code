import { pageMetadata } from "@/components/business/pageMetadata";

import { PrivacyTab } from "../_components/PrivacyTab";

export const generateMetadata = pageMetadata("settings/privacy");

/** Settings → Privacy: the data processing agreement and customers' data requests. */
export default function SettingsPrivacyPage() {
  return <PrivacyTab />;
}
