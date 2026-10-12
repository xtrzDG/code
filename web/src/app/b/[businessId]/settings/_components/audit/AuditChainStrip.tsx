"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { useBusiness, useBusinessFormat } from "@/components/business/BusinessContext";
import { Skeleton } from "@/components/ui";
import { AuditChainSummary } from "@/components/workspace/AuditChainSummary";

/**
 * The top of Settings → Audit: what the daily tamper check found in the
 * business's log (owners only; for anyone else the log below says why).
 */
export function AuditChainStrip() {
  const { business } = useBusiness();
  const format = useBusinessFormat();
  const chain = useQuery(queryKeys.settings.auditChain(business.id), () =>
    api.GET("/v1/businesses/{business_id}/audit-log/chain", { params: { path: { business_id: business.id } } }),
  );

  if (chain.error) {
    return null;
  }
  return (
    <div className="border-b border-line px-5 py-4 sm:px-6">
      {chain.data ? (
        <AuditChainSummary view={chain.data} formatWhen={(micros) => format.dateTime(micros)} />
      ) : (
        <Skeleton className="h-10 w-full max-w-md" />
      )}
    </div>
  );
}
