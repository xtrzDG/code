"use client";

import { useBusiness } from "@/components/business/BusinessContext";
import { IconUsers } from "@/components/icons";
import { ButtonLink, Card } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { businessPath } from "@/lib/navigation";

/** Customers' requests to export or erase their data are on each customer's page now: the way there. */
export function CustomerRequestsLink() {
  const { t } = useI18n();
  const { business } = useBusiness();
  return (
    <Card title={t("customers.privacyLink.title")} description={t("customers.privacyLink.body")}>
      <ButtonLink
        href={businessPath(business.id, "customers")}
        variant="secondary"
        leadingIcon={<IconUsers className="size-4" aria-hidden />}
      >
        {t("customers.privacyLink.link")}
      </ButtonLink>
    </Card>
  );
}
