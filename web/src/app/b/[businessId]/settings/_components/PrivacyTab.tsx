"use client";

import { CustomerRequestsLink } from "./privacy/CustomerRequestsLink";
import { DataExportCard } from "./privacy/DataExportCard";
import { DpaCard } from "./privacy/DpaCard";
import { RetentionCard } from "./privacy/RetentionCard";

/**
 * The data processing agreement, how long customers' data is kept, exports
 * of the business's data, and the way to customers' requests to export or
 * erase theirs (on each customer's page in Customers).
 */
export function PrivacyTab() {
  return (
    <div className="space-y-6">
      <DpaCard />
      <RetentionCard />
      <DataExportCard />
      <CustomerRequestsLink />
    </div>
  );
}
