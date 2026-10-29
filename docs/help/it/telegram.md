---
summary: Collega il tuo bot Telegram in due minuti con una chiave di @BotFather.
topic: channels
order: 10
keywords: telegram, bot, botfather, token, chiave, newbot, nome utente, username, collegare telegram
related: channels, inbox
status: needs_review
---
# Telegram

I tuoi clienti scrivono al tuo bot Telegram, con il nome e la foto della tua attività, e lì risponde l'assistente.

## Collegare

1. Apri **@BotFather** in Telegram e invia `/newbot`.
2. Scegli un nome (quello della tua attività) e un nome utente che finisca con `bot`, per esempio `cafe_batumi_bot`.
3. BotFather ti manda una chiave (token) simile a `123456789:AAH…`. Copiala.
4. Nel pannello apri **Assistente → [Canali](cabinet:assistant/channels)**, premi **Collega** sulla scheda di Telegram e incolla la chiave.

Fatto: scrivi al tuo bot dal tuo telefono e l'assistente ti risponde.

## Buono a sapersi

- Tieni segreta la chiave: chi ce l'ha controlla il bot. Il pannello la conserva cifrata e non la mostra mai più.
- Per cambiare la foto o la descrizione del bot, usa `/setuserpic` e `/setdescription` in @BotFather.
- Se invii `/revoke` a @BotFather, la vecchia chiave smette di funzionare: inserisci quella nuova con **Aggiorna i dati**.
- Le risposte del personale dalla pagina [Conversazioni](inbox) arrivano al cliente nella stessa chat di Telegram.
