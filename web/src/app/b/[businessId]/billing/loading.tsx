import { SectionLoading } from "@/components/business/SectionLoading";

import { BillingSkeleton } from "./_components/BillingSkeleton";

export default function BillingLoading() {
  return (
    <SectionLoading section="billing" label="common.loading">
      <BillingSkeleton />
    </SectionLoading>
  );
}
