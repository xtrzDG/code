---
summary: Connect your own Telegram bot in two minutes with a token from @BotFather.
topic: channels
order: 10
keywords: telegram, bot, botfather, token, newbot, username, connect telegram
related: channels, inbox
---
# Telegram

Your customers write to your own Telegram bot, with your business name and photo, and the assistant answers there.

## Connect

1. Open **@BotFather** in Telegram and send `/newbot`.
2. Choose a name (your business name) and a username that ends in `bot`, for example `cafe_batumi_bot`.
3. BotFather sends a token that looks like `123456789:AAH…`. Copy it.
4. In the cabinet open **Assistant → [Channels](cabinet:assistant/channels)**, press **Connect** on the Telegram card and paste the token.

That is all: write to your bot from your own phone and the assistant answers.

## Good to know

- Keep the token secret: anyone with it controls the bot. The cabinet stores it encrypted and never shows it again.
- To change the bot's photo or description, use `/setuserpic` and `/setdescription` in @BotFather.
- If you send `/revoke` in @BotFather, the old token stops working: enter the new one with **Update details**.
- Staff replies from the [Inbox](inbox) reach the customer in the same Telegram chat.
