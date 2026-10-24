import { pageMetadata } from "@/components/business/pageMetadata";

import { DepositsTab } from "../_components/DepositsTab";

export const generateMetadata = pageMetadata("settings/deposits");

/** Settings → Deposits: on or off, the hold, the refund window, the payment pages and the banquet deposit. */
export default function SettingsDepositsPage() {
  return <DepositsTab />;
}
