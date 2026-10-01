import { sectionMetadata } from "@/components/business/SectionPlaceholder";

import { BillingScreen } from "./BillingScreen";

export const generateMetadata = sectionMetadata("billing");

export default async function BillingPage({ searchParams }: PageProps<"/b/[businessId]/billing">) {
  const { checkout } = await searchParams;
  return <BillingScreen isCheckoutReturn={checkout === "return"} />;
}
