---
summary: Leiten Sie verpasste Anrufe mit einem Code je Fall an den Assistenten weiter, bei jedem Mobilfunkanbieter.
topic: channels
order: 50
keywords: rufumleitung, umleitung, telefon, anrufe, verpasste anrufe, besetzt, keine antwort, nicht erreichbar, anbieter, netzbetreiber, magti, silknet, cellfie, gsm-code, **61, **67, **62, ##002#
related: channels, inbox
status: needs_review
---
# Rufumleitung

Das Team nimmt weiterhin zuerst ab. Anrufe, die es verpasst oder die kommen, während die Leitung besetzt oder das Telefon aus ist, gehen an den Assistenten: Er nimmt ab, bucht und schickt Ihnen eine Zusammenfassung des Anrufs.

## Einschalten

Zuerst brauchen Sie die Nummer des Assistenten: Verbinden Sie den Kanal **Telefon** unter **Assistent → [Kanäle](cabinet:assistant/channels)**. Die Seite zeigt dann die Codes mit Ihrer Nummer bereits eingesetzt.

Nehmen Sie das Telefon mit der SIM-Karte, deren Nummer Kunden anrufen, wählen Sie jeden Code und drücken Sie auf Anrufen:

| Wann | Code |
| --- | --- |
| Sie nehmen nicht ab | `**61*number#` |
| Die Leitung ist besetzt | `**67*number#` |
| Das Telefon ist aus oder ohne Empfang | `**62*number#` |
| Alle Umleitungen ausschalten | `##002#` |

Warten Sie nach jedem Code auf die Bestätigung des Anbieters auf dem Bildschirm. Prüfen Sie dann: Rufen Sie Ihre Nummer von einem anderen Telefon an und nehmen Sie nicht ab; der Assistent sollte abnehmen.

## Nach Anbieter

- **Magti** veröffentlicht genau diese Codes (*61 keine Antwort, *67 besetzt, *62 nicht erreichbar).
- **Silknet** und **Cellfie** sowie die meisten Anbieter in anderen Ländern akzeptieren dieselben Standard-GSM-Codes. Funktioniert ein Code nicht, kann der Anbieter die Umleitung in seiner App oder über seinen Support einschalten.

## Gut zu wissen

- Festnetzanschlüsse und Telefonanlagen (PBX) richten die Umleitung in ihren eigenen Einstellungen ein; fragen Sie, wer sie betreut.
- Wenn Sie den Telefonkanal trennen, wählen Sie auch `##002#`, sonst hören Anrufer, dass die Nummer nicht erreichbar ist.
- Unter **Einstellungen → [Anrufe](cabinet:settings/calls)** können Sie Anrufern, die nicht durchgekommen sind, eine Nachricht zurückschicken.
