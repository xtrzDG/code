---
summary: Verbinden Sie Ihren eigenen Telegram-Bot in zwei Minuten mit einem Schlüssel von @BotFather.
topic: channels
order: 10
keywords: telegram, bot, botfather, token, schlüssel, newbot, benutzername, telegram verbinden
related: channels, inbox
status: needs_review
---
# Telegram

Ihre Kunden schreiben Ihrem eigenen Telegram-Bot, mit Ihrem Unternehmensnamen und Foto, und der Assistent antwortet dort.

## Verbinden

1. Öffnen Sie **@BotFather** in Telegram und senden Sie `/newbot`.
2. Wählen Sie einen Namen (Ihren Unternehmensnamen) und einen Benutzernamen, der auf `bot` endet, zum Beispiel `cafe_batumi_bot`.
3. BotFather sendet einen Schlüssel, der aussieht wie `123456789:AAH…`. Kopieren Sie ihn.
4. Öffnen Sie im Dashboard **Assistent → [Kanäle](cabinet:assistant/channels)**, klicken Sie auf der Telegram-Karte auf **Verbinden** und fügen Sie den Schlüssel ein.

Das war's: Schreiben Sie Ihrem Bot von Ihrem eigenen Telefon, und der Assistent antwortet.

## Gut zu wissen

- Halten Sie den Schlüssel geheim: Wer ihn hat, steuert den Bot. Das Dashboard speichert ihn verschlüsselt und zeigt ihn nie wieder an.
- Foto oder Beschreibung des Bots ändern Sie mit `/setuserpic` und `/setdescription` bei @BotFather.
- Senden Sie `/revoke` an @BotFather, funktioniert der alte Schlüssel nicht mehr: Geben Sie den neuen über **Angaben aktualisieren** ein.
- Antworten des Teams aus dem [Posteingang](inbox) erreichen den Kunden im selben Telegram-Chat.
