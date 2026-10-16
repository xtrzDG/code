import { pageMetadata } from "@/components/business/pageMetadata";

import { AuditTab } from "../_components/AuditTab";

export const generateMetadata = pageMetadata("settings/audit");

/** Settings → Audit log: who did what, with server filters. */
export default function SettingsAuditPage() {
  return <AuditTab />;
}
