import { pageMetadata } from "@/components/business/pageMetadata";

import { IntegrationsTab } from "../_components/IntegrationsTab";

export const generateMetadata = pageMetadata("settings/integrations");

/** Settings → Integrations: the calendars and booking systems the business works with, and how they stand. */
export default function SettingsIntegrationsPage() {
  return <IntegrationsTab />;
}
