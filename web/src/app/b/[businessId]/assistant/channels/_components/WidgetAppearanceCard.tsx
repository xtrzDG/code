"use client";

import { useState, type FormEvent } from "react";

import { api } from "@/api/client";
import { useMutation } from "@/api/useMutation";
import { useBusiness } from "@/components/business/BusinessContext";
import { Badge, Button, Card, Field, Fieldset, Input, Radio, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import type { ChannelView } from "../_lib/channels";
import {
  isSameWidgetLook,
  normalizeHexColor,
  savedWidgetLook,
  WIDGET_COLOR_PRESETS,
  WIDGET_DEFAULT_COLOR,
  WIDGET_POSITIONS,
  type WidgetLook,
  type WidgetPosition,
} from "../_lib/widgetLook";
import { WidgetPreviewFrame } from "./WidgetPreviewFrame";

/**
 * The website chat's brand colour and launcher corner (saved on the web
 * chat channel; the widget reads them from its config) beside a live
 * preview that follows every choice before it is saved.
 */
export function WidgetAppearanceCard({
  channel,
  canManage,
  onSaved,
}: {
  channel: ChannelView;
  canManage: boolean;
  onSaved: (channel: ChannelView) => void;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const saved = savedWidgetLook(channel);
  const [colorText, setColorText] = useState(saved.color);
  const [position, setPosition] = useState<WidgetPosition>(saved.position);
  const [showColorError, setShowColorError] = useState(false);

  const color = normalizeHexColor(colorText);
  const draft: WidgetLook = { color: color ?? saved.color, position };
  const isChanged = color === null || !isSameWidgetLook(draft, saved);

  const save = useMutation((look: WidgetLook) =>
    api.PUT("/v1/businesses/{business_id}/channels/{channel}", {
      params: { path: { business_id: business.id, channel: "web" } },
      body: { widget_color: look.color, widget_position: look.position },
    }),
  );

  const chooseColor = (value: string) => {
    setColorText(value);
    setShowColorError(false);
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (color === null) {
      setShowColorError(true);
      return;
    }
    const result = await save.run({ color, position });
    if (result.ok) {
      onSaved(result.data);
      setColorText(savedWidgetLook(result.data).color);
      toast.success(t("channels.widget.savedToast"));
    }
  };

  return (
    <Card
      title={t("channels.widget.lookTitle")}
      description={t("channels.widget.lookDescription")}
      actions={canManage && isChanged ? <Badge tone="warning">{t("channels.widget.unsaved")}</Badge> : undefined}
    >
      <div className="grid grid-cols-[minmax(0,1fr)] gap-6 xl:grid-cols-[minmax(0,1fr)_32rem]">
        <form noValidate onSubmit={onSubmit} className="min-w-0 space-y-5">
          <Field
            label={t("channels.widget.colorLabel")}
            hint={t("channels.widget.colorHint")}
            error={showColorError && color === null ? t("channels.widget.colorInvalid") : undefined}
          >
            {(control) => (
              <div className="flex flex-wrap items-center gap-3">
                <input
                  type="color"
                  aria-label={t("channels.widget.colorPicker")}
                  value={draft.color}
                  disabled={!canManage}
                  onChange={(event) => chooseColor(event.target.value)}
                  className="h-10 w-12 shrink-0 cursor-pointer rounded-lg border border-line bg-surface p-1 disabled:cursor-not-allowed disabled:opacity-60"
                />
                <Input
                  {...control}
                  value={colorText}
                  dir="ltr"
                  spellCheck={false}
                  autoComplete="off"
                  maxLength={7}
                  disabled={!canManage}
                  className="w-32 font-mono"
                  onChange={(event) => chooseColor(event.target.value)}
                  onBlur={() => setShowColorError(true)}
                />
              </div>
            )}
          </Field>

          <div className="space-y-2">
            <p id="widget-presets" className="text-sm font-medium text-ink">
              {t("channels.widget.presets")}
            </p>
            <div role="group" aria-labelledby="widget-presets" className="flex flex-wrap gap-2">
              {WIDGET_COLOR_PRESETS.map((preset) => {
                const isSelected = draft.color === preset;
                return (
                  <button
                    key={preset}
                    type="button"
                    disabled={!canManage}
                    aria-pressed={isSelected}
                    aria-label={
                      preset === WIDGET_DEFAULT_COLOR
                        ? `${t("channels.widget.preset", { color: preset })} — ${t("channels.widget.defaultColor")}`
                        : t("channels.widget.preset", { color: preset })
                    }
                    title={preset}
                    onClick={() => chooseColor(preset)}
                    style={{ backgroundColor: preset }}
                    className={cn(
                      "size-9 rounded-full border border-line-strong transition-transform focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus disabled:cursor-not-allowed disabled:opacity-60",
                      isSelected ? "ring-2 ring-ink ring-offset-2 ring-offset-surface" : "hover:scale-105",
                    )}
                  />
                );
              })}
            </div>
          </div>

          <Fieldset legend={t("channels.widget.positionLabel")}>
            <div className="flex flex-wrap gap-x-6 gap-y-2">
              {WIDGET_POSITIONS.map((option) => (
                <Radio
                  key={option}
                  name="widget-position"
                  value={option}
                  checked={position === option}
                  disabled={!canManage}
                  onChange={() => setPosition(option)}
                  label={option === "left" ? t("channels.widget.positionLeft") : t("channels.widget.positionRight")}
                />
              ))}
            </div>
          </Fieldset>

          {canManage ? (
            <Button type="submit" size="sm" isLoading={save.isPending} loadingText={t("channels.widget.saving")} disabled={!isChanged}>
              {t("channels.widget.save")}
            </Button>
          ) : null}
        </form>

        <WidgetPreviewFrame look={draft} />
      </div>
    </Card>
  );
}
