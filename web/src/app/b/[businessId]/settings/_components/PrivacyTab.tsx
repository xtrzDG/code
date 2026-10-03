"use client";

import { DataRequestsCard } from "./privacy/DataRequestsCard";
import { DpaCard } from "./privacy/DpaCard";

/** The data processing agreement and customers' requests to export or erase their data. */
export function PrivacyTab() {
  return (
    <div className="space-y-6">
      <DpaCard />
      <DataRequestsCard />
    </div>
  );
}
