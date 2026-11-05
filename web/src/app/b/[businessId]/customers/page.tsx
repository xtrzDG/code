import { pageMetadata } from "@/components/business/pageMetadata";

import { parseCustomerFilters } from "./_lib/customerFilters";
import { CustomersScreen } from "./CustomersScreen";

export const generateMetadata = pageMetadata("customers");

/** Customers; the search and filters come from the URL (`?q=nino&tag=regular&show=vip`). */
export default async function CustomersPage({ searchParams }: PageProps<"/b/[businessId]/customers">) {
  return <CustomersScreen initialFilters={parseCustomerFilters(await searchParams)} />;
}
