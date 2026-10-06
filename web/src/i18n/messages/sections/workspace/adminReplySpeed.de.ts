/** `adminReplySpeed.*` in German (a draft awaiting native review). */

import type { Translation } from "../../../translate";
import type { adminReplySpeedEn } from "./adminReplySpeed.en";

export const adminReplySpeedDe: Translation<typeof adminReplySpeedEn> = {
  title: "Antwortgeschwindigkeit, 7 Tage",
  description: "Wie lange Kunden gewartet haben, von ihrer ersten unbeantworteten Nachricht bis zur Antwort des Assistenten.",
  median: "Typische Wartezeit (Median)",
  p95: "19 von 20 Antworten innerhalb von",
  replies: "Gemessene Antworten",
  slowNote: "Mehr als eine von zwanzig Antworten dauerte über 15 Sekunden. Prüfen Sie den Modellanbieter und die Werkzeuge des Unternehmens.",
  empty: "Keine gemessenen Antworten in den letzten 7 Tagen. Chats werden ab diesem Release gemessen; Anrufe und der Test-Chat nicht.",
  tableCaption: "Antwortgeschwindigkeit nach Kanal",
  channel: "Kanal",
  channelReplies: "Antworten",
  channelMedian: "Median",
  channelP95: "95 %",
  seconds: "{value} s",
  minutes: "{value} Min.",
  issueLabel: "Langsame Antworten",
};
