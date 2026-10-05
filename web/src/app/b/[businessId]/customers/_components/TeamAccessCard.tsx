"use client";

/**
 * Owners decide whether staff see customers' full phone numbers (off by
 * default: staff see a masked one). The change is audited by the API.
 */

import { useId } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import type { Query } from "@/api/useQuery";
import type { Schema } from "@/api/types";
import { useBusiness } from "@/components/business/BusinessContext";
import { Switch } from "@/components/content/Switch";
import { Card, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

type CustomerSettings = Schema<"CustomerSettingsView">;

export function TeamAccessCard({ settings }: { settings: Query<CustomerSettings> }) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const hintId = useId();
  const save = useMutation(
    (staffSeesPhones: boolean) =>
      api.PUT("/v1/businesses/{business_id}/customer-settings", {
        params: { path: { business_id: business.id } },
        body: { staff_sees_phone_numbers: staffSeesPhones },
      }),
    {
      optimistic: (staffSeesPhones) => {
        const before = settings.data;
        settings.setData((current) => (current ? { ...current, staff_sees_phone_numbers: staffSeesPhones } : current));
        return () => settings.setData(() => before);
      },
      invalidate: [queryKeys.customers.settings(business.id)],
    },
  );

  const isOn = settings.data?.staff_sees_phone_numbers ?? false;
  const onChange = async (checked: boolean) => {
    const result = await save.run(checked);
    if (result.ok) {
      toast.success(t(checked ? "customers.access.on" : "customers.access.off"));
    }
  };

  return (
    <Card title={t("customers.access.title")}>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-sm font-medium text-ink">{t("customers.access.staffPhones")}</p>
          <p id={hintId} className="mt-1 text-sm text-ink-muted">
            {t("customers.access.staffPhonesHint")}
          </p>
        </div>
        <Switch
          checked={isOn}
          onChange={(checked) => void onChange(checked)}
          label={t("customers.access.staffPhones")}
          describedBy={hintId}
          disabled={!settings.data || save.isPending}
        />
      </div>
    </Card>
  );
}
