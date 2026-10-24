/**
 * Device notifications in the end-to-end suite, without a real push service:
 *
 *  - `startPushService()`: a local HTTP server standing in for FCM or
 *    Mozilla's push service (the API accepts 127.0.0.1 outside production);
 *    it records what the API posts and answers 201.
 *  - `mockBrowserPush(page, …)`: the browser's Push API (permission, the
 *    service worker registration, `pushManager.subscribe`) answering with a
 *    subscription at that server, for keys the test holds.
 *  - `decryptPush(body, receiver)`: reads a posted message as the browser
 *    would (RFC 8291, aes128gcm), so the test sees the notification itself.
 */

import { createDecipheriv, createECDH, createHmac, randomBytes } from "node:crypto";
import { createServer, type IncomingHttpHeaders } from "node:http";
import type { AddressInfo } from "node:net";

import type { Page } from "@playwright/test";

export interface ReceivedPush {
  path: string;
  headers: IncomingHttpHeaders;
  body: Buffer;
}

export interface PushService {
  endpoint: string;
  received: ReceivedPush[];
  close: () => Promise<void>;
}

export async function startPushService(): Promise<PushService> {
  const received: ReceivedPush[] = [];
  const server = createServer((request, response) => {
    const chunks: Buffer[] = [];
    request.on("data", (chunk: Buffer) => chunks.push(chunk));
    request.on("end", () => {
      received.push({ path: request.url ?? "", headers: request.headers, body: Buffer.concat(chunks) });
      response.writeHead(201, { location: "/message/1" }).end();
    });
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address() as AddressInfo;
  return {
    endpoint: `http://127.0.0.1:${port}/push/${randomBytes(6).toString("hex")}`,
    received,
    close: () => new Promise((resolve) => server.close(() => resolve())),
  };
}

export interface Receiver {
  privateKey: Buffer;
  publicKey: Buffer;
  auth: Buffer;
}

const base64Url = (bytes: Buffer) => bytes.toString("base64url");

/** The browser side of a subscription: its P-256 key pair and auth secret. */
export function newReceiver(): Receiver {
  const ecdh = createECDH("prime256v1");
  ecdh.generateKeys();
  return { privateKey: ecdh.getPrivateKey(), publicKey: ecdh.getPublicKey(), auth: randomBytes(16) };
}

/** Makes the page's Push API subscribe at `endpoint` with the receiver's keys. */
export async function mockBrowserPush(page: Page, endpoint: string, receiver: Receiver): Promise<void> {
  await page.addInitScript(
    ({ endpoint: address, p256dh, auth }) => {
      type FakeSubscription = {
        endpoint: string;
        options: { applicationServerKey: ArrayBuffer };
        toJSON: () => PushSubscriptionJSON;
        unsubscribe: () => Promise<boolean>;
      };
      // The browser keeps its subscription across page loads, as a real one does.
      const SAVED = "__e2ePushSubscriptionKey";
      const subscriptionFor = (key: ArrayBuffer): FakeSubscription => ({
        endpoint: address,
        options: { applicationServerKey: key },
        toJSON: () => ({ endpoint: address, expirationTime: null, keys: { p256dh, auth } }),
        unsubscribe: async () => {
          subscription = null;
          store(null);
          return true;
        },
      });
      const store = (value: string | null) => {
        try {
          if (value === null) {
            localStorage.removeItem(SAVED);
          } else {
            localStorage.setItem(SAVED, value);
          }
        } catch {
          // A frame without storage (about:blank): nothing to keep.
        }
      };
      let saved: string | null = null;
      try {
        saved = localStorage.getItem(SAVED);
      } catch {
        saved = null;
      }
      let subscription: FakeSubscription | null = saved
        ? subscriptionFor(Uint8Array.from(JSON.parse(saved) as number[]).buffer)
        : null;
      const pushManager = {
        getSubscription: async () => subscription,
        subscribe: async (options: { applicationServerKey: Uint8Array }) => {
          const key = options.applicationServerKey;
          store(JSON.stringify(Array.from(key)));
          subscription = subscriptionFor(key.buffer.slice(key.byteOffset, key.byteOffset + key.byteLength) as ArrayBuffer);
          return subscription;
        },
      };
      let registration: object | null = null;
      if (saved) {
        registration = { scope: `${location.origin}/`, pushManager, active: { postMessage: () => undefined } };
      }
      const register = () => (registration ??= { scope: `${location.origin}/`, pushManager, active: { postMessage: () => undefined } });
      const serviceWorker = {
        getRegistration: async () => registration ?? undefined,
        register: async () => register(),
        get ready() {
          return Promise.resolve(register());
        },
        addEventListener: () => undefined,
        removeEventListener: () => undefined,
      };
      Object.defineProperty(Navigator.prototype, "serviceWorker", { configurable: true, get: () => serviceWorker });
      Object.defineProperty(window, "PushManager", { configurable: true, value: function PushManager() {} });
      let permission: NotificationPermission = saved ? "granted" : "default";
      Object.defineProperty(window, "Notification", {
        configurable: true,
        value: {
          get permission() {
            return permission;
          },
          requestPermission: async () => (permission = "granted"),
        },
      });
    },
    { endpoint, p256dh: base64Url(receiver.publicKey), auth: base64Url(receiver.auth) },
  );
}

function hkdf(salt: Buffer, secret: Buffer, info: Buffer, length: number): Buffer {
  const key = createHmac("sha256", salt).update(secret).digest();
  return createHmac("sha256", key).update(Buffer.concat([info, Buffer.from([1])])).digest().subarray(0, length);
}

/** The plaintext of an aes128gcm Web Push message, as the receiving browser decrypts it. */
export function decryptPush(body: Buffer, receiver: Receiver): string {
  const salt = body.subarray(0, 16);
  const idLength = body[20]!;
  const senderPublic = body.subarray(21, 21 + idLength);
  const ciphertext = body.subarray(21 + idLength);
  const ecdh = createECDH("prime256v1");
  ecdh.setPrivateKey(receiver.privateKey);
  const shared = ecdh.computeSecret(senderPublic);
  const keyInfo = Buffer.concat([Buffer.from("WebPush: info\0"), receiver.publicKey, senderPublic]);
  const ikm = hkdf(receiver.auth, shared, keyInfo, 32);
  const contentKey = hkdf(salt, ikm, Buffer.from("Content-Encoding: aes128gcm\0"), 16);
  const nonce = hkdf(salt, ikm, Buffer.from("Content-Encoding: nonce\0"), 12);
  const decipher = createDecipheriv("aes-128-gcm", contentKey, nonce);
  decipher.setAuthTag(ciphertext.subarray(ciphertext.length - 16));
  const padded = Buffer.concat([decipher.update(ciphertext.subarray(0, ciphertext.length - 16)), decipher.final()]);
  // The last record ends with the delimiter 2, then zero padding.
  const end = padded.lastIndexOf(2);
  return padded.subarray(0, end).toString("utf8");
}
