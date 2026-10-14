"""The confirmation step: write actions wait here until the user replies "yes".

A write tool never acts directly. It calls propose(), which stores the action
for that chat. bot.py (or the terminal chat) then shows the exact action, and
only runs it when the user's next message is exactly "yes". The model is not
involved in that decision, so it cannot approve anything by itself.
"""

# One waiting action per chat: {chat_id: {"description": ..., "function": ..., "args": ...}}
# Lives in memory only - restarting the bot drops anything still waiting.
pending = {}

APPROVE_WORDS = ("yes", "y")


def propose(chat_id, description, function, /, **args):
    """Store an action to run later, once the user approves. Returns text for the model.

    **args collects any named arguments into a dictionary, e.g.
    propose(1, "...", f, title="Gym") gives args == {"title": "Gym"}.

    The / marks the first three as positional-only, so an action that itself
    takes a chat_id argument (like gcal.create_event) can be passed
    chat_id=... without colliding with this function's own chat_id.
    """
    pending[chat_id] = {"description": description, "function": function, "args": args}
    return (
        f"NOT DONE YET - waiting for the user's approval: {description}. "
        "Tell the user what you propose; the app itself will ask them to reply yes."
    )


def pending_description(chat_id):
    """The description of this chat's waiting action, or None if nothing is waiting."""
    action = pending.get(chat_id)
    if action is None:
        return None
    return action["description"]


def approval_prompt(chat_id):
    """The exact text shown to the user under the bot's answer, or "" if nothing is waiting."""
    description = pending_description(chat_id)
    if description is None:
        return ""
    return f"\n\n⚠️ Waiting for approval: {description}\nReply yes to confirm. Anything else cancels."


def handle_reply(chat_id, text):
    """Deal with a message from a chat that has a waiting action.

    Returns the reply to send, or None if nothing was waiting (then the
    message is handled normally by the agent).
    """
    # .pop removes the action and returns it, so it can never run twice.
    action = pending.pop(chat_id, None)
    if action is None:
        return None

    if text.strip().lower() not in APPROVE_WORDS:
        return "Cancelled. Nothing was done."

    try:
        result = action["function"](**action["args"])
    except Exception as error:
        return f"Approved, but it failed: {error}"
    return f"Done: {result}"
