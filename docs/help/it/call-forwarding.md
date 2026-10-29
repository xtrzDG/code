---
summary: Manda all'assistente le chiamate che perdi, con un codice per ogni caso, con qualsiasi operatore mobile.
topic: channels
order: 50
keywords: inoltro di chiamata, inoltro chiamate, deviazione di chiamata, trasferimento di chiamata, telefono, chiamate, chiamate perse, occupato, nessuna risposta, non raggiungibile, operatore, gestore, tim, vodafone, windtre, iliad, codice gsm, **61, **67, **62, ##002#
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

## Buono a sapersi

- Le linee fisse e i centralini (PBX) impostano l'inoltro nelle loro impostazioni; chiedi a chi se ne occupa.
- Se scolleghi il canale Telefono, componi anche `##002#`, altrimenti chi chiama sentirà che il numero non è disponibile.
- Da **Impostazioni → [Chiamate](cabinet:settings/calls)** puoi mandare un SMS a chi ha chiamato senza riuscire a parlare con nessuno.
