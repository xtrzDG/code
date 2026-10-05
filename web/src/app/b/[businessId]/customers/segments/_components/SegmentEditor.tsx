"use client";

/**
 * Creating or changing a segment: a name and the rules every member must
 * meet (a tag, the last visit more than N days ago, at least / at most so
 * many bookings, VIPs only), with a live count of who matches as the
 * owner types.
 */

import { useEffect, useId, useState, type FormEvent } from "react";

import { api } from "@/api/client";
import { queryKeys } from "@/api/queryKeys";
import { useMutation } from "@/api/useMutation";
import { useQuery } from "@/api/useQuery";
import { useBusiness } from "@/components/business/BusinessContext";
import { Button, Checkbox, Field, InlineError, Input, Modal, ModalFooter, useToast } from "@/components/ui";
import { useI18n } from "@/i18n/client";

import {
  EMPTY_SEGMENT_FORM,
  formOf,
  MAX_SEGMENT_NAME,
  rulesKey,
  rulesOf,
  segmentBody,
  type Segment,
  type SegmentErrors,
  type SegmentForm,
  type SegmentRules,
} from "../_lib/segmentRules";

const PREVIEW_DELAY_MS = 400;

function SegmentPreviewLine({ rules }: { rules: SegmentRules | null }) {
  const { t, tp } = useI18n();
  const { business } = useBusiness();
  const [asked, setAsked] = useState<SegmentRules | null>(rules);
  useEffect(() => {
    const timer = window.setTimeout(() => setAsked(rules), PREVIEW_DELAY_MS);
    return () => window.clearTimeout(timer);
  }, [rules]);
  const key = asked ? rulesKey(asked) : "";
  const preview = useQuery(
    queryKeys.customers.preview(business.id, key),
    () =>
      api.POST("/v1/businesses/{business_id}/customer-segments/preview", {
        params: { path: { business_id: business.id } },
        body: asked ?? { vip_only: false },
      }),
    { enabled: asked !== null, staleMs: 15_000, keepPreviousData: true },
  );
  const data = preview.data;
  const text =
    !data || preview.isLoading
      ? t("segments.preview.counting")
      : data.member_count === 0
        ? t("segments.preview.none")
        : tp(data.is_count_exact ? "segments.preview.count" : "segments.preview.atLeast", data.member_count);
  return (
    <p className="text-sm font-medium text-ink" role="status" aria-live="polite" aria-busy={preview.isFetching}>
      {text}
    </p>
  );
}

export function SegmentEditor({
  open,
  segment,
  knownTags,
  onClose,
}: {
  open: boolean;
  /** The segment to change; null for a new one. */
  segment: Segment | null;
  knownTags: readonly string[];
  onClose: () => void;
}) {
  const { t } = useI18n();
  const toast = useToast();
  const { business } = useBusiness();
  const tagListId = useId();
  const [form, setForm] = useState<SegmentForm>(EMPTY_SEGMENT_FORM);
  const [errors, setErrors] = useState<SegmentErrors>({});
  const [openedFor, setOpenedFor] = useState<{ open: boolean; segment: Segment | null }>({ open, segment });

  // Every opening starts from the segment (or empty).
  if (openedFor.open !== open || openedFor.segment !== segment) {
    setOpenedFor({ open, segment });
    if (open) {
      setForm(segment ? formOf(segment) : EMPTY_SEGMENT_FORM);
      setErrors({});
    }
  }

  const save = useMutation(
    (body: NonNullable<ReturnType<typeof segmentBody>["body"]>) =>
      segment
        ? api.PUT("/v1/businesses/{business_id}/customer-segments/{segment_id}", {
            params: { path: { business_id: business.id, segment_id: segment.id } },
            body,
          })
        : api.POST("/v1/businesses/{business_id}/customer-segments", {
            params: { path: { business_id: business.id } },
            body,
          }),
    {
      errorToast: false,
      invalidate: (saved) => [
        queryKeys.customers.segments(business.id),
        ...(saved ? [queryKeys.customers.members(business.id, saved.id)] : []),
      ],
    },
  );

  const set = <Key extends keyof SegmentForm>(key: Key, value: SegmentForm[Key]) => {
    setForm((current) => ({ ...current, [key]: value }));
    setErrors((current) => ({ ...current, [key]: undefined }));
  };

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const { body, errors: found } = segmentBody(form);
    setErrors(found);
    if (!body) {
      return;
    }
    const result = await save.run(body);
    if (result.ok) {
      toast.success(t("segments.saved"));
      onClose();
    }
  };

  const { rules } = rulesOf(form);
  const error = (key: keyof SegmentErrors) => (errors[key] ? t(errors[key]) : undefined);

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={t(segment ? "segments.editor.editTitle" : "segments.editor.newTitle")}
      description={t("segments.editor.rulesHint")}
    >
      <form onSubmit={(event) => void onSubmit(event)} className="space-y-4" noValidate>
        <Field label={t("segments.editor.name")} error={error("name")} required>
          {(control) => (
            <Input
              {...control}
              value={form.name}
              maxLength={MAX_SEGMENT_NAME}
              placeholder={t("segments.editor.namePlaceholder")}
              onChange={(event) => set("name", event.target.value)}
            />
          )}
        </Field>
        <fieldset className="space-y-4">
          <legend className="text-sm font-semibold text-ink">{t("segments.editor.rules")}</legend>
          <Field label={t("segments.editor.tag")}>
            {(control) => (
              <>
                <Input
                  {...control}
                  value={form.tag}
                  maxLength={32}
                  list={tagListId}
                  placeholder={t("segments.editor.anyTag")}
                  onChange={(event) => set("tag", event.target.value)}
                />
                <datalist id={tagListId}>
                  {knownTags.map((tag) => (
                    <option key={tag} value={tag} />
                  ))}
                </datalist>
              </>
            )}
          </Field>
          <Field label={t("segments.editor.lastVisit")} error={error("lastVisitDays")}>
            {(control) => (
              <Input
                {...control}
                inputMode="numeric"
                value={form.lastVisitDays}
                maxLength={4}
                onChange={(event) => set("lastVisitDays", event.target.value)}
              />
            )}
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label={t("segments.editor.minBookings")} error={error("minBookings")}>
              {(control) => (
                <Input
                  {...control}
                  inputMode="numeric"
                  value={form.minBookings}
                  maxLength={5}
                  onChange={(event) => set("minBookings", event.target.value)}
                />
              )}
            </Field>
            <Field label={t("segments.editor.maxBookings")} error={error("maxBookings")}>
              {(control) => (
                <Input
                  {...control}
                  inputMode="numeric"
                  value={form.maxBookings}
                  maxLength={5}
                  onChange={(event) => set("maxBookings", event.target.value)}
                />
              )}
            </Field>
          </div>
          <Checkbox
            label={t("segments.editor.vipOnly")}
            checked={form.vipOnly}
            onChange={(event) => set("vipOnly", event.target.checked)}
          />
        </fieldset>
        <div className="rounded-xl bg-surface-muted px-4 py-3">
          <SegmentPreviewLine rules={rules} />
        </div>
        <InlineError error={save.error} overrides={{ conflict: "segments.limit" }} />
        <ModalFooter>
          <Button type="button" variant="secondary" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button type="submit" isLoading={save.isPending}>
            {t("segments.editor.save")}
          </Button>
        </ModalFooter>
      </form>
    </Modal>
  );
}
