"""OmniAgent on Telegram: every text message goes through the agent loop.

Run with: python bot.py   (stop with Ctrl+C)
"""
import openai
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, MessageHandler, filters

import approvals
import config
import memory
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

    # Is a write action waiting for approval? Then this message is the answer
    # to it. Code decides here - the model is not asked.
    outcome = approvals.handle_reply(chat_id, text)
    if outcome is not None:
        history.append({"role": "user", "content": text})
        history.append({"role": "assistant", "content": outcome})
        histories[chat_id] = history[-MAX_HISTORY:]
        await update.message.reply_text(outcome)
        return

    history.append({"role": "user", "content": text})

    # Shows "typing..." at the top of the chat while the agent thinks.
    await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

    try:
        answer = run_agent(history, chat_id)
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

    # If a tool proposed a write action, show exactly what will run - written
    # by our code, so the model cannot misdescribe it.
    answer += approvals.approval_prompt(chat_id)

    history.append({"role": "assistant", "content": answer})

    # Keep only the newest MAX_HISTORY messages.
    histories[chat_id] = history[-MAX_HISTORY:]

    await update.message.reply_text(answer)

async def reset(update, context):
    chat_id = update.effective_chat.id
    histories[chat_id] = []
    await update.message.reply_text("Conversation history has been reset.")


async def list_memories(update, context):
    """Runs on /memories: show every fact saved for this chat, with its id."""
    # Always the sender's own chat - never config.MY_CHAT_ID, or anyone could
    # read the owner's facts.
    chat_id = update.effective_chat.id
    facts = memory.get_facts(chat_id)

    if not facts:
        await update.message.reply_text("I don't remember anything about you yet.")
        return

    text = "What I remember about you:\n"
    for fact_id, fact in facts:
        text += f"#{fact_id}: {fact}\n"
    text += "\nTo delete one, send /forget followed by its number, e.g. /forget 3"
    await update.message.reply_text(text)


async def forget(update, context):
    """Runs on /forget <id>: delete one of this chat's facts."""
    chat_id = update.effective_chat.id

    # context.args is the list of words after the command:
    # "/forget 3" gives ["3"], and "/forget" alone gives [].
    if not context.args:
        await update.message.reply_text("Which one? Send /forget followed by its number, e.g. /forget 3")
        return

    # The words arrive as text. Turn "3" into the number 3.
    try:
        fact_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(f"'{context.args[0]}' is not a number. Send /memories to see the numbers.")
        return

    if memory.delete_fact(chat_id, fact_id):
        await update.message.reply_text(f"Forgotten fact #{fact_id}.")
    else:
        await update.message.reply_text(f"I have no fact #{fact_id} for you. Send /memories to see the list.")


def main():
    # The Application is the library's engine: it polls Telegram and hands
    # each new message to the matching handler below.
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    # filters.TEXT & ~filters.COMMAND means "text, but not a /command".
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("memories", list_memories))
    app.add_handler(CommandHandler("forget", forget))

    print("Bot is running. Message it on Telegram. Press Ctrl+C to stop.")
    app.run_polling()
    
if __name__ == "__main__":
    main()
