/**
 * A Server-Sent Events parser (the text/event-stream format of the HTML
 * standard) for streams read with fetch: chunks go in as they arrive,
 * complete messages come out. Comments (": heartbeat") only count as
 * activity; `id:` sets the last event id the stream asks to resume from.
 */

export interface ServerSentEvent {
  /** The id of this message, or null when it had none. */
  id: string | null;
  /** The message's name (`event:`), "message" when it had none. */
  event: string;
  /** The `data:` lines joined by newlines. */
  data: string;
}

const LINE_BREAK = /\r\n|\r|\n/;

export class EventStreamParser {
  private buffer = "";
  private dataLines: string[] = [];
  private eventName = "";
  private messageId: string | null = null;

  /** The last `id:` seen, kept across messages (Last-Event-ID on reconnect). */
  lastEventId: string | null = null;
  /** The server's `retry:` advice in milliseconds, if it sent one. */
  retryMs: number | null = null;

  /** Feeds a decoded chunk; returns the messages it completed. */
  push(chunk: string): ServerSentEvent[] {
    this.buffer += chunk;
    const lines = this.buffer.split(LINE_BREAK);
    // A trailing "\r" may be the first half of "\r\n": keep it for the next chunk.
    this.buffer = this.buffer.endsWith("\r") ? `${lines.pop() ?? ""}\r` : (lines.pop() ?? "");
    if (this.buffer === "\r") {
      lines.push("");
      this.buffer = "";
    }
    const messages: ServerSentEvent[] = [];
    for (const line of lines) {
      const message = this.readLine(line);
      if (message) {
        messages.push(message);
      }
    }
    return messages;
  }

  private readLine(line: string): ServerSentEvent | null {
    if (line === "") {
      return this.dispatch();
    }
    if (line.startsWith(":")) {
      return null;
    }
    const colon = line.indexOf(":");
    const field = colon === -1 ? line : line.slice(0, colon);
    let value = colon === -1 ? "" : line.slice(colon + 1);
    if (value.startsWith(" ")) {
      value = value.slice(1);
    }
    if (field === "data") {
      this.dataLines.push(value);
    } else if (field === "event") {
      this.eventName = value;
    } else if (field === "id" && !value.includes("\0")) {
      this.messageId = value;
      this.lastEventId = value;
    } else if (field === "retry" && /^\d+$/.test(value)) {
      this.retryMs = Number(value);
    }
    return null;
  }

  private dispatch(): ServerSentEvent | null {
    const message: ServerSentEvent | null =
      this.dataLines.length === 0
        ? null
        : { id: this.messageId, event: this.eventName || "message", data: this.dataLines.join("\n") };
    this.dataLines = [];
    this.eventName = "";
    this.messageId = null;
    return message;
  }
}
