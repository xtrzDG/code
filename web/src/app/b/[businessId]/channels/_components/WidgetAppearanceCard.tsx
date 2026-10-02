"use client";

import { useState, type FormEvent } from "react";

import { api } from "@/api/client";
import { useApiMutation } from "@/api/hooks";
import { useBusiness } from "@/components/business/BusinessContext";
import { IconExternal } from "@/components/icons";
import { Badge, Button, Card, Field, Fieldset, Input, Radio, buttonClasses, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";
import { cn } from "@/lib/cn";

import type { ChannelView } from "../_lib/channels";
import {
  buildWidgetPreviewUrl,
  isSameWidgetLook,
  normalizeHexColor,
  readableTextColor,
  savedWidgetLook,
  WIDGET_COLOR_PRESETS,
  WIDGET_DEFAULT_COLOR,
  WIDGET_POSITIONS,
  type WidgetLook,
  type WidgetPosition,
} from "../_lib/widgetLook";

/**
 * The website chat's brand colour and launcher corner (saved on the web
 * chat channel; the widget reads them from its config), a sketch of the
 * page and a link to the live preview with the choices made here.
 */
export function WidgetAppearanceCard({
  channel,
  demoUrl,
  canManage,
  onSaved,
}: {
  channel: ChannelView;
  demoUrl: string | undefined;
  canManage: boolean;
  onSaved: (channel: ChannelView) => void;
}) {
  const { t, locale } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const saved = savedWidgetLook(channel);
  const [colorText, setColorText] = useState(saved.color);
  const [position, setPosition] = useState<WidgetPosition>(saved.position);
  const [showColorError, setShowColorError] = useState(false);

  const color = normalizeHexColor(colorText);
  const draft: WidgetLook = { color: color ?? saved.color, position };
  const isChanged = color === null || !isSameWidgetLook(draft, saved);

  const save = useApiMutation((look: WidgetLook) =>
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

  const previewUrl = demoUrl ? buildWidgetPreviewUrl(demoUrl, draft, locale) : null;

  return (
    <Card
      title={t("channels.widget.lookTitle")}
      description={t("channels.widget.lookDescription")}
      actions={canManage && isChanged ? <Badge tone="warning">{t("channels.widget.unsaved")}</Badge> : undefined}
    >
      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_16rem]">
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

          <p className="text-xs text-ink-subtle">{t("channels.widget.overrideNote")}</p>

          <div className="flex flex-wrap items-center gap-2">
            {canManage ? (
              <Button type="submit" size="sm" isLoading={save.isPending} loadingText={t("channels.widget.saving")} disabled={!isChanged}>
                {t("channels.widget.save")}
              </Button>
            ) : null}
            {previewUrl ? (
              <a
                href={previewUrl}
                target="_blank"
                rel="noopener noreferrer"
                className={buttonClasses({ variant: "secondary", size: "sm" })}
                aria-describedby="widget-preview-hint"
              >
                <IconExternal className="size-4" aria-hidden />
                <span>{t("channels.widget.openPreview")}</span>
              </a>
            ) : null}
          </div>
          {previewUrl ? (
            <p id="widget-preview-hint" className="text-xs text-ink-subtle">
              {t("channels.widget.previewHint")}
            </p>
          ) : null}
        </form>

        <PageSketch look={draft} label={t("channels.widget.previewAlt")} />
      </div>
    </Card>
  );
}

/** A tiny page with the chat button in the chosen corner and colour. */
function PageSketch({ look, label }: { look: WidgetLook; label: string }) {
  return (
    <div
      role="img"
      aria-label={label}
      className="relative mx-auto aspect-[4/3] w-full max-w-64 self-start overflow-hidden rounded-xl border border-line bg-surface-muted"
    >
      <div className="flex items-center gap-1 border-b border-line bg-surface px-2 py-1.5" aria-hidden>
        <span className="size-1.5 rounded-full bg-line-strong" />
        <span className="size-1.5 rounded-full bg-line-strong" />
        <span className="size-1.5 rounded-full bg-line-strong" />
      </div>
      <div className="space-y-2 p-3" aria-hidden>
        <div className="h-2.5 w-3/5 rounded bg-line-strong/70" />
        <div className="h-2 w-4/5 rounded bg-line" />
        <div className="h-2 w-2/3 rounded bg-line" />
        <div className="h-2 w-3/4 rounded bg-line" />
      </div>
      <span
        aria-hidden
        className={cn(
          "absolute bottom-3 flex size-9 items-center justify-center rounded-full shadow-md",
          look.position === "left" ? "left-3" : "right-3",
        )}
        style={{ backgroundColor: look.color, color: readableTextColor(look.color) }}
      >
        <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 12a8 8 0 0 1-11.8 7.04L4 20l1.05-4.2A8 8 0 1 1 21 12z" />
        </svg>
      </span>
    </div>
  );
}
