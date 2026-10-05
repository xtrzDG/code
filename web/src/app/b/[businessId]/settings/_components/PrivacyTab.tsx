"use client";

import { DataExportCard } from "./privacy/DataExportCard";
import { DataRequestsCard } from "./privacy/DataRequestsCard";
import { DpaCard } from "./privacy/DpaCard";
import { RetentionCard } from "./privacy/RetentionCard";

/**
 * The data processing agreement, how long customers' data is kept, exports
 * of the business's data and customers' requests to export or erase theirs.
 */
export function PrivacyTab() {
  return (
    <div className="space-y-6">
      <DpaCard />
      <RetentionCard />
      <DataExportCard />
      <DataRequestsCard />
    </div>
  );
}
