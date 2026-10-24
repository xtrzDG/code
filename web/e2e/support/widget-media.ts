/**
 * The fake widget API of support/widget-site.ts with photos, voice messages
 * and the thumbs: the uploads the widget makes (POST .../attachments, a
 * multipart part "file" and the visitor key in a header), the messages that
 * name them and the ratings (POST .../rating). Like the real API, an answer
 * of a turn that booked invites a rating (`invites_rating`).
 */

import type { Route } from "@playwright/test";

import { FakeWidgetApi } from "./widget-site";

const CORS_HEADERS = {
  "access-control-allow-origin": "*",
  "access-control-allow-methods": "GET, POST, OPTIONS",
  "access-control-allow-headers": "Content-Type, X-Widget-Session-Key",
};

/** A 1×1 PNG: what a visitor's photo looks like to the fake API. */
export const PNG_PHOTO = Buffer.from(
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
  "base64",
);

/** What the config says the chat takes (the API's widget_attachment_rules). */
export const ATTACHMENT_RULES = {
  image_types: ["image/jpeg", "image/png", "image/webp"],
  audio_types: ["audio/webm", "audio/ogg", "audio/mp4"],
  max_image_bytes: 10_485_760,
  max_voice_bytes: 16_777_216,
  max_voice_seconds: 120,
};

interface Upload {
  /** The file part's declared type, as the browser sent it. */
  contentType: string;
  sessionKey: string | null;
  size: number;
}

interface Rating {
  session_key: string;
  rating: string;
  reason?: string;
  message_id?: string;
}

type Author = Parameters<FakeWidgetApi["add"]>[0];

export class FakeMediaWidgetApi extends FakeWidgetApi {
  uploads: Upload[] = [];
  /** The upload ids of each message that named some. */
  sentAttachments: string[][] = [];
  ratings: Rating[] = [];
  /** The next upload is refused (422) with this reason code. */
  refuseUploadWith: string | null = null;
  /** The next answer is one of a turn that booked: the thumbs show at once. */
  nextAnswerInvitesRating = false;
  /** The next message with files is refused (422) with this reason code. */
  refuseMessageWith: string | null = null;
  /** The next message with files is queued but its answer never arrives. */
  loseNextMessageAnswer = false;
  private uploadCount = 0;
  /** Uploads already sent with a message: a second message is refused. */
  private claimed = new Set<string>();

  constructor() {
    super();
    this.configExtras = { attachments: ATTACHMENT_RULES };
  }

  override add(author: Author, text: string, direction: "ltr" | "rtl" = "ltr") {
    const message = super.add(author, text, direction);
    if (author === "assistant" && this.nextAnswerInvitesRating) {
      this.nextAnswerInvitesRating = false;
      Object.assign(message, { invites_rating: true });
    }
    return message;
  }

  override async handle(route: Route): Promise<void> {
    const request = route.request();
    const path = new URL(request.url()).pathname;
    if (request.method() === "POST" && path.endsWith("/attachments")) {
      await this.upload(route);
      return;
    }
    if (request.method() === "POST" && path.endsWith("/rating")) {
      const body = JSON.parse(request.postData() ?? "{}") as Rating;
      this.ratings.push(body);
      await route.fulfill({ status: 200, headers: CORS_HEADERS, json: { rating: body.rating, reason: body.reason ?? null } });
      return;
    }
    const body = request.method() === "POST" ? (JSON.parse(request.postData() ?? "{}") as Record<string, unknown>) : {};
    if (path.endsWith("/messages") && Array.isArray(body.attachment_ids)) {
      await this.messageWithFiles(route, body, body.attachment_ids as string[]);
      return;
    }
    await super.handle(route);
  }

  /**
   * A message with files: accepted (202) and answered, like the API; refused
   * (422) when asked to, or when its files already went with a message.
   */
  private async messageWithFiles(route: Route, body: Record<string, unknown>, ids: string[]): Promise<void> {
    const code = ids.some((id) => this.claimed.has(id)) ? "attachment_already_sent" : this.refuseMessageWith;
    if (code) {
      this.refuseMessageWith = null;
      await route.fulfill({
        status: 422,
        headers: CORS_HEADERS,
        json: { error: "validation_failed", message: "Refused.", reasons: [{ code, message: "Refused.", details: ids }] },
      });
      return;
    }
    ids.forEach((id) => this.claimed.add(id));
    this.sentAttachments.push(ids);
    this.sessionKeys.push(String(body.session_key));
    this.add("customer", typeof body.text === "string" ? body.text : "");
    this.add("assistant", `Answer to ${ids.length} file(s)`);
    if (this.loseNextMessageAnswer) {
      // Queued, but the connection broke before the widget heard back.
      this.loseNextMessageAnswer = false;
      await route.abort("connectionreset");
      return;
    }
    await route.fulfill({ status: 202, headers: CORS_HEADERS, json: { event_id: "inbound_event_files" } });
  }

  private async upload(route: Route): Promise<void> {
    const request = route.request();
    const raw = request.postDataBuffer() ?? Buffer.alloc(0);
    const head = raw.subarray(0, 600).toString("latin1");
    this.uploads.push({
      contentType: /name="file"[^\r\n]*\r\nContent-Type: ([^\r\n]+)/.exec(head)?.[1] ?? "",
      sessionKey: request.headers()["x-widget-session-key"] ?? null,
      size: raw.length,
    });
    if (this.refuseUploadWith) {
      const code = this.refuseUploadWith;
      this.refuseUploadWith = null;
      await route.fulfill({
        status: 422,
        headers: CORS_HEADERS,
        json: { error: "validation_failed", message: "Refused.", reasons: [{ code, message: "Refused.", details: [] }] },
      });
      return;
    }
    this.uploadCount += 1;
    const id = `widget_upload_00000000-0000-4000-8000-${String(this.uploadCount).padStart(12, "0")}`;
    await route.fulfill({
      status: 201,
      headers: CORS_HEADERS,
      json: { attachment_id: id, kind: "image", media_type: "image/png", byte_count: raw.length },
    });
  }
}
