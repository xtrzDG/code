/**
 * Pure helpers of the billing details ("Реквизиты для счетов") and the
 * invoice and receipt downloads of the Billing page.
 *
 * Fields of the API this relies on: GET/PUT …/billing/profile
 * (`BillingProfileView`: legal_name, tax_id, address, billing_email,
 * country_code, is_saved, tax_treatment, tax_rate_basis_points) and
 * GET …/billing/invoices/{id}/documents/{invoice|receipt} (a PDF with
 * `Content-Disposition: attachment`).
 */

import type { Schema } from "@/api/types";
import type { MessageKey } from "@/i18n/translate";
import { looksLikeEmail } from "@/lib/countries";
import { REGION_NAMES } from "@/lib/displayNames.generated";
import { formatNumber } from "@/lib/format";

import type { InvoiceView } from "./billing";

export type BillingProfileView = Schema<"BillingProfileView">;
export type TaxTreatment = Schema<"TaxTreatment">;
export type BillingDocumentKind = "invoice" | "receipt";

/** The body of PUT …/billing/profile. */
export interface BillingProfileBody {
  legal_name: string;
  tax_id: string | null;
  address: string | null;
  billing_email: string | null;
  country_code: string;
}

export interface BillingDetailsForm {
  legalName: string;
  taxId: string;
  address: string;
  billingEmail: string;
  countryCode: string;
}

export type BillingDetailsField = "legalName" | "taxId" | "address" | "billingEmail";
export type BillingDetailsErrors = Partial<Record<BillingDetailsField, MessageKey>>;

/** Limits of the API (BillingLegalName, TaxpayerIdentificationNumber, BillingAddressText). */
export const MAX_LEGAL_NAME_LENGTH = 200;
export const MAX_TAX_ID_LENGTH = 40;
export const MAX_ADDRESS_LENGTH = 400;
const MIN_ADDRESS_LENGTH = 3;
const MIN_TAX_ID_LENGTH = 2;
const TAX_ID_PATTERN = /^[A-Za-z0-9](?:[A-Za-z0-9 ./-]*[A-Za-z0-9])?$/;

/**
 * Region codes of the name table that are no country an invoice can name
 * (the API's `is_billing_country` refuses them): Antarctica, Clipperton,
 * Sark, the EU and eurozone, outlying Oceania, the UN, pseudo-locales and
 * "unknown".
 */
const NOT_BILLING_COUNTRIES = new Set(["AQ", "CP", "CQ", "EU", "EZ", "QO", "UN", "XA", "XB", "ZZ"]);

export const VAT_TEXTS: Record<TaxTreatment, MessageKey> = {
  not_registered: "billing.details.vat.not_registered",
  standard: "billing.details.vat.standard",
  reverse_charge: "billing.details.vat.reverse_charge",
  outside_scope: "billing.details.vat.outside_scope",
};

export function billingDetailsForm(view: BillingProfileView): BillingDetailsForm {
  return {
    legalName: view.legal_name,
    taxId: view.tax_id ?? "",
    address: view.address ?? "",
    billingEmail: view.billing_email ?? "",
    countryCode: view.country_code,
  };
}

/** Blank optional fields are sent as null; e-mail addresses in lower case like the API keeps them. */
export function billingProfileBody(form: BillingDetailsForm): BillingProfileBody {
  const optional = (value: string) => (value.trim() === "" ? null : value.trim());
  const email = optional(form.billingEmail);
  return {
    legal_name: form.legalName.trim(),
    tax_id: optional(form.taxId),
    address: optional(form.address.replace(/\r\n?/g, "\n")),
    billing_email: email === null ? null : email.toLowerCase(),
    country_code: form.countryCode,
  };
}

export function billingDetailsErrors(form: BillingDetailsForm): BillingDetailsErrors {
  const errors: BillingDetailsErrors = {};
  if (form.legalName.trim() === "") {
    errors.legalName = "billing.details.errors.legalName";
  }
  const taxId = form.taxId.trim();
  if (taxId !== "" && (taxId.length < MIN_TAX_ID_LENGTH || !TAX_ID_PATTERN.test(taxId))) {
    errors.taxId = "billing.details.errors.taxId";
  }
  const address = form.address.trim();
  if (address !== "" && address.length < MIN_ADDRESS_LENGTH) {
    errors.address = "billing.details.errors.address";
  }
  const email = form.billingEmail.trim();
  if (email !== "" && !looksLikeEmail(email)) {
    errors.billingEmail = "billing.details.errors.billingEmail";
  }
  return errors;
}

export function hasDetailsErrors(errors: BillingDetailsErrors): boolean {
  return Object.keys(errors).length > 0;
}

/** Whether the form says what is stored already (nothing to save). */
export function isSameBillingDetails(form: BillingDetailsForm, view: BillingProfileView): boolean {
  if (!view.is_saved) {
    return false;
  }
  const body = billingProfileBody(form);
  return (
    body.legal_name === view.legal_name &&
    body.tax_id === (view.tax_id ?? null) &&
    body.address === (view.address ?? null) &&
    body.billing_email === (view.billing_email ?? null) &&
    body.country_code === view.country_code
  );
}

/** Country codes an invoice can name, sorted by their name in `locale`; `current` stays listed. */
export function billingCountryCodes(nameOf: (code: string) => string, current: string, locale: string): string[] {
  const codes = Object.keys(REGION_NAMES.en ?? {}).filter((code) => /^[A-Z]{2}$/.test(code) && !NOT_BILLING_COUNTRIES.has(code));
  if (!codes.includes(current)) {
    codes.push(current);
  }
  const names = new Map(codes.map((code) => [code, nameOf(code)]));
  return codes.sort((left, right) => (names.get(left) ?? left).localeCompare(names.get(right) ?? right, locale));
}

/** 1800 basis points -> "18%" ("18 %" in Russian), in the reader's number format. */
export function formatTaxRate(basisPoints: number, locale: string): string {
  return formatNumber(basisPoints / 10_000, locale, { style: "percent", maximumFractionDigits: 2 });
}

/**
 * The file name a download is saved under: RFC 5987 `filename*` first,
 * then `filename`, else `fallback`. Only letters, digits, dots, dashes and
 * underscores are kept.
 */
export function fileNameFromDisposition(header: string | null, fallback: string): string {
  if (header) {
    const extended = /filename\*\s*=\s*(?:UTF-8|utf-8)''([^;]+)/.exec(header);
    const plain = /filename\s*=\s*"?([^";]+)"?/.exec(header);
    let raw: string | undefined;
    try {
      raw = extended?.[1] ? decodeURIComponent(extended[1].trim()) : plain?.[1]?.trim();
    } catch {
      raw = plain?.[1]?.trim();
    }
    const cleaned = (raw ?? "").replace(/[^\w.-]+/g, "-").replace(/^[-.]+/, "");
    if (cleaned !== "") {
      return cleaned;
    }
  }
  return fallback;
}

/** The invoice PDF exists for every invoice but a voided one that never got a number. */
export function canDownloadInvoice(invoice: Pick<InvoiceView, "status" | "number">): boolean {
  return invoice.status !== "void" || Boolean(invoice.number);
}

/** Saves a downloaded file in the browser. */
export function saveFile(blob: Blob, fileName: string): void {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  link.rel = "noopener";
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1_000);
}
