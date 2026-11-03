"use client";

import { useId } from "react";

import { Switch } from "@/components/content/Switch";
import { useBusiness } from "@/components/business/BusinessContext";
import { Card, ErrorState, SkeletonCard, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import {
  SWITCHABLE_ACTIONS,
  actionLabel,
  assistantControls,
  controlsBody,
  controlsChangeText,
  withAction,
  type AssistantControls,
  type SwitchableAction,
} from "../../_lib/assistantControls";
import type { AssistantSettingsView } from "../../_lib/customerMemory";
import { useAssistantSettings } from "../../_lib/useAssistantSettings";

/**
 * An owner's kill switches of the assistant: pass every customer to the
 * team (messages wait in the inbox, calls go to the forwarding number) and
 * switch single actions off. Each switch saves at once; staff see them,
 * owners change them.
 */
export function AssistantControlsCard() {
  const { t } = useI18n();
  const { settings } = useAssistantSettings();
  return (
    <Card title={t("assistantControls.title")} description={t("assistantControls.description")} data-testid="assistant-controls">
      {settings.data ? (
        <ControlsForm view={settings.data} />
      ) : settings.error ? (
        <ErrorState error={settings.error} onRetry={settings.reload} className="py-4" />
      ) : (
        <SkeletonCard lines={4} />
      )}
    </Card>
  );
}

function ControlsForm({ view }: { view: AssistantSettingsView }) {
  const { t } = useI18n();
  const toast = useToast();
  const { isOwner } = useBusiness();
  const { settings, save } = useAssistantSettings();
  const handOverHint = useId();
  const actionsHint = useId();
  const controls = assistantControls(view);
  const disabled = !isOwner || save.isPending;

  const change = async (next: AssistantControls) => {
    const result = await save.run(controlsBody(view, next));
    if (result.ok) {
      settings.setData(result.data);
      const text = controlsChangeText(controls, assistantControls(result.data));
      if (text !== null) {
        toast.success(t(text));
      }
    }
  };

  const switchAction = (action: SwitchableAction, isOn: boolean) =>
    void change({ ...controls, disabledActions: withAction(controls.disabledActions, action, isOn) });

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 space-y-1">
          <p className="text-sm font-medium text-ink">{t("assistantControls.handOver.label")}</p>
          <p id={handOverHint} className="text-sm text-ink-muted">
            {t("assistantControls.handOver.hint")}
          </p>
        </div>
        <Switch
          checked={controls.isHandedOver}
          onChange={(isHandedOver) => void change({ ...controls, isHandedOver })}
          label={t("assistantControls.handOver.label")}
          describedBy={handOverHint}
          disabled={disabled}
        />
      </div>
      <div className="rounded-xl bg-surface-muted px-4 py-3">
        <p className="text-sm font-medium text-ink">{t("assistantControls.actions.title")}</p>
        <p id={actionsHint} className="mt-1 text-sm text-ink-muted">
          {t("assistantControls.actions.hint")}
        </p>
        <ul className="mt-3 space-y-3">
          {SWITCHABLE_ACTIONS.map((action) => (
            <li key={action} className="flex items-center justify-between gap-4">
              <span className="min-w-0 text-sm text-ink">{t(actionLabel(action))}</span>
              <Switch
                checked={!controls.disabledActions.includes(action)}
                onChange={(isOn) => switchAction(action, isOn)}
                label={t(actionLabel(action))}
                describedBy={actionsHint}
                disabled={disabled}
              />
            </li>
          ))}
        </ul>
      </div>
      {isOwner ? null : <p className="text-xs text-ink-subtle">{t("assistantControls.ownerOnly")}</p>}
    </div>
  );
}
