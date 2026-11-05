import { SectionFrame } from "@/components/shell/SectionFrame";

/** Customers: the list with each customer's page, and (owners) the saved segments, under one heading with tabs. */
export default function CustomersLayout({ children }: LayoutProps<"/b/[businessId]/customers">) {
  return <SectionFrame section="customers">{children}</SectionFrame>;
}
