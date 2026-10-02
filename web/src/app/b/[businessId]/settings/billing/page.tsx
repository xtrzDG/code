import { pageMetadata } from "@/components/business/pageMetadata";

import { BillingScreen } from "./BillingScreen";

export const generateMetadata = pageMetadata("settings/billing");

export default async function BillingPage({ searchParams }: PageProps<"/b/[businessId]/billing">) {
  const { checkout } = await searchParams;
  return <BillingScreen isCheckoutReturn={checkout === "return"} />;
}
