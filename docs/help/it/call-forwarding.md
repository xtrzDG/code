---
summary: Manda all'assistente le chiamate che perdi, con un codice per ogni caso, con qualsiasi operatore mobile.
topic: channels
order: 50
keywords: inoltro di chiamata, inoltro chiamate, deviazione di chiamata, trasferimento di chiamata, telefono, chiamate, chiamate perse, occupato, nessuna risposta, non raggiungibile, operatore, gestore, tim, vodafone, windtre, iliad, verizon, t-mobile, at&t, stati uniti, usa, codice gsm, **61, **67, **62, ##002#, *71, *73, ##004#
related: channels, inbox
status: needs_review
---
# Inoltro di chiamata

Il personale continua a rispondere per primo. Le chiamate che perde, o che arrivano mentre la linea è occupata o il telefono è spento, passano all'assistente: risponde, prende le prenotazioni e ti manda un riepilogo della chiamata.

## Attivarlo

Prima ti serve il numero dell'assistente: collega il canale **Telefono** in **Assistente → [Canali](cabinet:assistant/channels)**. La pagina mostra poi i codici con il tuo numero già inserito.

Prendi il telefono con la SIM del numero che chiamano i clienti, componi ogni codice e avvia la chiamata:

| Quando | Codice |
| --- | --- |
| Non rispondi | `**61*number#` |
| La linea è occupata | `**67*number#` |
| Il telefono è spento o senza campo | `**62*number#` |
| Disattivare tutti gli inoltri | `##002#` |

Dopo ogni codice aspetta la conferma dell'operatore sullo schermo. Poi fai una prova: chiama il tuo numero da un altro telefono e non rispondere; deve rispondere l'assistente.

## Per operatore

- **TIM**, **Vodafone**, **WindTre** e **Iliad**, come la maggior parte degli operatori mobili, accettano questi codici GSM standard.
- Se un codice non funziona, l'operatore può attivare l'inoltro dalla sua app o tramite il suo servizio clienti.

## Negli Stati Uniti

Negli Stati Uniti i codici cambiano da operatore a operatore, quindi per un'attività negli Stati Uniti la pagina elenca prima **Verizon**, **T-Mobile** e **AT&T**: apri il tuo operatore e componi i suoi codici uno alla volta. Per gli altri operatori ci sono i codici standard in **Altri operatori**. Per il numero dell'assistente +1 212-555-0123 la pagina mostra:

| Operatore | Codici |
| --- | --- |
| Verizon | `*712125550123` (nessuna risposta o occupato: un solo codice per entrambi), `*73` (disattiva) |
| T-Mobile | `**61*12125550123#`, `**67*12125550123#`, `**62*12125550123#`, `##004#` (disattiva; ripristina la segreteria) |
| AT&T | `**61*2125550123#`, `**67*2125550123#`, `**62*2125550123#`, `##002#` |
| Altri operatori | `**61*12125550123#`, `**67*12125550123#`, `**62*12125550123#`, `##002#` |

- Nessuno di questi codici è ancora confermato con l'operatore, e la pagina lo segnala: se un codice non funziona, chiedi al tuo operatore.
- Verizon inoltra dopo che il telefono ha squillato da 3 a 6 volte e non ha un codice per il telefono spento o senza copertura: quelle chiamate vanno comunque in segreteria.
- Con T-Mobile la segreteria è già l'inoltro per mancata risposta, quindi il codice per la mancata risposta la sostituisce. Per far squillare il telefono più a lungo, inserisci `**25` o `**30` (secondi) prima dell'ultimo `#` del codice per la mancata risposta.
- Su iPhone, se le chiamate senza risposta vanno ancora in segreteria, disattiva Segreteria live (Live Voicemail) nelle impostazioni di Telefono.
- La pagina non mostra mai un codice che inoltra tutte le chiamate (il `*72` di Verizon, i codici `*21*`): il tuo personale continua a rispondere per primo.

## Buono a sapersi

- Le linee fisse e i centralini (PBX) impostano l'inoltro nelle loro impostazioni; chiedi a chi se ne occupa.
- Se scolleghi il canale Telefono, componi anche `##002#` (con Verizon `*73`, con T-Mobile `##004#`), altrimenti chi chiama sentirà che il numero non è disponibile.
- Da **Impostazioni → [Chiamate](cabinet:settings/calls)** puoi scrivere a chi ha chiamato senza riuscire a parlare con nessuno: su WhatsApp e, dove si può inviare, con un SMS (la pagina dice quando non si può).
