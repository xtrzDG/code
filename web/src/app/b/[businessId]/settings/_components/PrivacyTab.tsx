"use client";

import { DataExportCard } from "./privacy/DataExportCard";
import { DataRequestsCard } from "./privacy/DataRequestsCard";
import { DpaCard } from "./privacy/DpaCard";

/** The data processing agreement, exports of the business's data and customers' requests to export or erase theirs. */
export function PrivacyTab() {
  return (
    <div className="space-y-6">
      <DpaCard />
      <DataExportCard />
      <DataRequestsCard />
    </div>
  );
}
