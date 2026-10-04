"""bot.py handlers, driven with fake Telegram objects and a fake agent."""
import asyncio
from types import SimpleNamespace

import pytest

import approvals
import bot
import memory
from conftest import FRIEND, OWNER


class FakeMessage:
    def __init__(self, text=""):
        self.text = text
        self.replies = []

    async def reply_text(self, text):
        self.replies.append(text)


class FakeBot:
    async def send_chat_action(self, chat_id, action):
        pass


def send(handler, chat_id, text="", args=None):
    """Run one handler as if Telegram delivered a message; return the bot's reply."""
    message = FakeMessage(text)
    update = SimpleNamespace(effective_chat=SimpleNamespace(id=chat_id), message=message)
    context = SimpleNamespace(bot=FakeBot(), args=args or [])
    asyncio.run(handler(update, context))
    return message.replies[-1]


@pytest.fixture(autouse=True)
def fake_agent(monkeypatch):
    """Replace the real agent: echo the message, and propose a write for 'add ...'."""
    ran = []

    def agent(history, chat_id):
        text = history[-1]["content"]
        if text.startswith("add"):
            approvals.propose(chat_id, "Create event 'Gym'", lambda: ran.append("Gym") or "created Gym")
            return "Sure."
        return f"echo: {text} ({len(history)} in history)"

    bot.histories.clear()
    monkeypatch.setattr(bot, "run_agent", agent)
    return ran


def test_each_chat_has_its_own_history():
    send(bot.handle_message, OWNER, "hi")
    assert send(bot.handle_message, OWNER, "again") == "echo: again (3 in history)"
    assert send(bot.handle_message, FRIEND, "hello") == "echo: hello (1 in history)"


def test_history_is_trimmed():
    for i in range(15):
        send(bot.handle_message, OWNER, f"message {i}")
    assert len(bot.histories[OWNER]) == bot.MAX_HISTORY


def test_write_waits_for_yes(fake_agent):
    reply = send(bot.handle_message, OWNER, "add gym")
    assert "⚠️ Waiting for approval: Create event 'Gym'" in reply
    assert fake_agent == []
    assert send(bot.handle_message, OWNER, "yes") == "Done: created Gym"
    assert fake_agent == ["Gym"]


def test_reset_drops_waiting_action(fake_agent):
    send(bot.handle_message, OWNER, "add gym")
    send(bot.reset, OWNER)
    assert approvals.pending == {}
    assert send(bot.handle_message, OWNER, "yes").startswith("echo: yes")
    assert fake_agent == []


def test_memories_and_forget():
    fact_id = memory.add_fact(OWNER, "Loves cricket")
    assert f"#{fact_id}: Loves cricket" in send(bot.list_memories, OWNER)
    assert send(bot.list_memories, FRIEND) == "I don't remember anything about you yet."
    assert send(bot.forget, FRIEND, args=[str(fact_id)]).startswith("I have no fact")
    assert send(bot.forget, OWNER, args=[]).startswith("Which one?")
    assert send(bot.forget, OWNER, args=["abc"]).startswith("'abc' is not a number")
    assert send(bot.forget, OWNER, args=[str(fact_id)]) == f"Forgotten fact #{fact_id}."
    assert memory.get_facts(OWNER) == []
