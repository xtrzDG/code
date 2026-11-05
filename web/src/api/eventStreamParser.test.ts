import { describe, expect, it } from "vitest";

import { EventStreamParser } from "./eventStreamParser";

describe("the Server-Sent Events parser", () => {
  it("reads named events with ids across chunk boundaries", () => {
    const parser = new EventStreamParser();

    expect(parser.push("retry: 3000\n\nevent: stream.ready\nda")).toEqual([]);
    expect(parser.push('ta: {"a":1}\n\nid: 017-ab\nevent: booking.created\ndata: {"ids":[]}\n')).toEqual([
      { id: null, event: "stream.ready", data: '{"a":1}' },
    ]);
    expect(parser.push("\n")).toEqual([{ id: "017-ab", event: "booking.created", data: '{"ids":[]}' }]);
    expect(parser.lastEventId).toBe("017-ab");
    expect(parser.retryMs).toBe(3000);
  });

  it("skips comments, joins data lines and accepts any line break", () => {
    const parser = new EventStreamParser();

    const messages = parser.push(": heartbeat\r\n\r\ndata: one\r\ndata:two\rdata\n\r");
    messages.push(...parser.push("\n"));

    expect(messages).toEqual([{ id: null, event: "message", data: "one\ntwo\n" }]);
  });

  it("keeps the last id when a message has none and ignores ids with NUL", () => {
    const parser = new EventStreamParser();

    parser.push("id: first\ndata: x\n\ndata: y\n\nid: bad\0id\ndata: z\n\n");

    expect(parser.lastEventId).toBe("first");
  });

  it("dispatches nothing for a blank message without data", () => {
    const parser = new EventStreamParser();

    expect(parser.push("event: lonely\n\n")).toEqual([]);
    expect(parser.push("retry: soon\n\n")).toEqual([]);
    expect(parser.retryMs).toBeNull();
  });
});
