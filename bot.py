"""OmniAgent on Telegram: every text message goes through the agent loop.

Run with: python bot.py   (stop with Ctrl+C)
"""
import openai
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters

import config
from agent import run_agent

# Keep only the last 20 messages of each chat. Every message in the history is
# sent with every request, so without a limit requests grow slower and bigger
# until they hit the model's size limit.
MAX_HISTORY = 20

# One separate history per chat: {chat_id: [messages...]}.
# Lives in memory only - restarting the bot forgets every conversation.
histories = {}


async def start(update, context):
    """Runs when someone sends /start - the first message when a bot is opened."""
    await update.message.reply_text("Hello! I'm OmniAgent. Ask me anything.")


async def handle_message(update, context):
    """Runs for every ordinary text message: answer it with the agent."""
    chat_id = update.effective_chat.id
    text = update.message.text
    print(f"[debug] message from chat {chat_id}: {text}")

    # Get this chat's history, creating an empty one the first time.
    if chat_id not in histories:
        histories[chat_id] = []
    history = histories[chat_id]

    history.append({"role": "user", "content": text})

    # Shows "typing..." at the top of the chat while the agent thinks.
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    try:
        answer = run_agent(history)
    except openai.RateLimitError:
        history.pop()  # forget the unanswered question
        await update.message.reply_text("I'm rate limited right now. Please try again in a minute.")
        return
    except Exception as error:
        history.pop()
        print(f"[error] {error!r}")
        await update.message.reply_text("Sorry, something went wrong. Please try again.")
        return

    # Telegram refuses to send an empty message.
    if not answer:
        answer = "(I had nothing to say - try asking another way.)"

    history.append({"role": "assistant", "content": answer})

    # Keep only the newest MAX_HISTORY messages.
    histories[chat_id] = history[-MAX_HISTORY:]

    await update.message.reply_text(answer)

async def reset(update, context):
    chat_id = update.effective_chat.id
    histories[chat_id] = []
    await update.message.reply_text("Conversation history has been reset.")

def main():
    # The Application is the library's engine: it polls Telegram and hands
    # each new message to the matching handler below.
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    # filters.TEXT & ~filters.COMMAND means "text, but not a /command".
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CommandHandler("reset", reset))
    
    print("Bot is running. Message it on Telegram. Press Ctrl+C to stop.")
    app.run_polling()
    
if __name__ == "__main__":
    main()
