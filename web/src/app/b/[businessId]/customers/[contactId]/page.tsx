import { pageMetadata } from "@/components/business/pageMetadata";

import { CustomerScreen } from "./CustomerScreen";

export const generateMetadata = pageMetadata("customers");

/** One customer: their history across channels, the team's card, blocking and data requests. */
export default async function CustomerPage({ params }: PageProps<"/b/[businessId]/customers/[contactId]">) {
  const { contactId } = await params;
  return <CustomerScreen contactId={decodeURIComponent(contactId)} />;
}
