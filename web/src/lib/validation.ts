/**
 * zod helpers for forms. Messages are i18n keys, so one schema serves
 * every interface language:
 *
 *     const Name = z.string().trim().min(1, messageKey("validation.required"));
 *     const errors = fieldErrors(Schema.safeParse(values));  // { name: "validation.required" }
 *     <Field error={errors.name && t(errors.name)} …>
 */

import { z } from "zod";

import type { MessageKey } from "@/i18n/translate";

/** Type-checks an i18n key used as a zod message. */
export function messageKey(key: MessageKey): MessageKey {
  return key;
}

/** First message key per top-level field of a failed parse. */
export function fieldErrors<T>(result: z.ZodSafeParseResult<T>): Partial<Record<string, MessageKey>> {
  if (result.success) {
    return {};
  }
  const errors: Partial<Record<string, MessageKey>> = {};
  for (const issue of result.error.issues) {
    const field = String(issue.path[0] ?? "_");
    errors[field] ??= issue.message as MessageKey;
  }
  return errors;
}

/** An absolute http(s) link, as the API's WebLink accepts. */
export const webLinkSchema = z
  .string()
  .trim()
  .regex(/^https?:\/\/[^\s/]+(\/\S*)?$/, messageKey("validation.url"))
  .min(10, messageKey("validation.url"))
  .max(2048, messageKey("validation.url"));
