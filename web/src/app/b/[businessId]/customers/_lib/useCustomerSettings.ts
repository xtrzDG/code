"use client";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";

/** Whether staff see phones, and the business's tags (the tag filter, the card's suggestions). */
export function useCustomerSettings() {
  const { business } = useBusiness();
  return useQuery(queryKeys.customers.settings(business.id), () =>
    api.GET("/v1/businesses/{business_id}/customer-settings", { params: { path: { business_id: business.id } } }),
  );
}
