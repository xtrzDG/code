/** The Channels page's connect form: the fields each channel asks for and the PUT body. */

import type { RequestBody } from "@/api/types";

import type { ConnectableChannel } from "./channels";

export type ConnectChannelBody = RequestBody<"/v1/businesses/{business_id}/channels/{channel}", "put">;

export interface ConnectForm {
  botToken: string;
  phoneNumberId: string;
  businessAccountId: string;
  pageId: string;
  pageAccessToken: string;
  phoneNumber: string;
  countryHint: string;
}

export type ConnectField = keyof ConnectForm;

export const EMPTY_CONNECT_FORM: ConnectForm = {
  botToken: "",
  phoneNumberId: "",
  businessAccountId: "",
  pageId: "",
  pageAccessToken: "",
  phoneNumber: "",
  countryHint: "",
};

/** Fields each channel asks for (the website chat needs none). */
export const CHANNEL_FIELDS: Record<ConnectableChannel, readonly ConnectField[]> = {
  web_chat: [],
  telegram: ["botToken"],
  whatsapp: ["phoneNumberId", "businessAccountId"],
  instagram: ["pageId", "pageAccessToken"],
  messenger: ["pageId", "pageAccessToken"],
  phone: ["phoneNumber", "countryHint"],
};

/** Why a field was refused; the page maps these to texts. */
export type ConnectFieldError = "required" | "botToken" | "digits" | "pageToken";

/** Token from @BotFather: "<bot id>:<35 characters>" (the API checks the same shape). */
const BOT_TOKEN = /^[0-9]{5,20}:[A-Za-z0-9_-]{30,100}$/;
/** Whether a (whitespace-free) text has the shape of a token from @BotFather. */
export function isBotToken(token: string): boolean {
  return BOT_TOKEN.test(token);
}

/** Meta object ids (phone number id, business account id, page id). */
const META_ID = /^[0-9]{1,32}$/;
const MIN_PAGE_TOKEN_LENGTH = 20;
const MAX_PAGE_TOKEN_LENGTH = 1024;

function isPageToken(token: string): boolean {
  return (
    token.length >= MIN_PAGE_TOKEN_LENGTH &&
    token.length <= MAX_PAGE_TOKEN_LENGTH &&
    /^[\x21-\x7e]+$/.test(token)
  );
}

export type ConnectFormResult =
  | { ok: true; body: ConnectChannelBody }
  | { ok: false; errors: Partial<Record<ConnectField, ConnectFieldError>> };

/**
 * The PUT body for a channel from the form, or the fields to fix. Values
 * are trimmed; only the channel's own fields are sent.
 */
export function buildConnectBody(kind: ConnectableChannel, form: ConnectForm): ConnectFormResult {
  const value = (field: ConnectField) => form[field].trim();
  const errors: Partial<Record<ConnectField, ConnectFieldError>> = {};

  switch (kind) {
    case "web_chat":
      return { ok: true, body: {} };
    case "telegram": {
      const token = value("botToken").replace(/\s+/g, "");
      if (token === "") {
        errors.botToken = "required";
      } else if (!BOT_TOKEN.test(token)) {
        errors.botToken = "botToken";
      }
      return Object.keys(errors).length > 0 ? { ok: false, errors } : { ok: true, body: { bot_token: token } };
    }
    case "whatsapp": {
      const phoneNumberId = value("phoneNumberId");
      const accountId = value("businessAccountId");
      if (phoneNumberId === "") {
        errors.phoneNumberId = "required";
      } else if (!META_ID.test(phoneNumberId)) {
        errors.phoneNumberId = "digits";
      }
      if (accountId !== "" && !META_ID.test(accountId)) {
        errors.businessAccountId = "digits";
      }
      if (Object.keys(errors).length > 0) {
        return { ok: false, errors };
      }
      return {
        ok: true,
        body: {
          phone_number_id: phoneNumberId,
          ...(accountId ? { whatsapp_business_account_id: accountId } : {}),
        },
      };
    }
    case "instagram":
    case "messenger": {
      const pageId = value("pageId");
      const token = value("pageAccessToken");
      if (pageId === "") {
        errors.pageId = "required";
      } else if (!META_ID.test(pageId)) {
        errors.pageId = "digits";
      }
      if (token === "") {
        errors.pageAccessToken = "required";
      } else if (!isPageToken(token)) {
        errors.pageAccessToken = "pageToken";
      }
      return Object.keys(errors).length > 0
        ? { ok: false, errors }
        : { ok: true, body: { page_id: pageId, page_access_token: token } };
    }
    case "phone": {
      const phoneNumber = value("phoneNumber");
      const countryHint = value("countryHint").toUpperCase();
      if (phoneNumber === "") {
        errors.phoneNumber = "required";
        return { ok: false, errors };
      }
      return {
        ok: true,
        body: { phone_number: phoneNumber, ...(/^[A-Z]{2}$/.test(countryHint) ? { country_hint: countryHint } : {}) },
      };
    }
  }
}
