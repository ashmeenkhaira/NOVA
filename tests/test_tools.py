import approvals
import memory
import tokens
import tools
from conftest import FRIEND, OWNER

EVENT = '{"title": "Gym", "start": "2026-10-06T07:00", "end": "2026-10-06T08:00"}'


def test_menu_only_shows_what_the_api_needs():
    for entry in tools.tool_menu():
        assert set(entry["function"]) == {"name", "description", "parameters"}


def test_errors_come_back_as_text():
    assert tools.run_tool("fly_to_moon", "{}", OWNER).startswith("Error: there is no tool")
    assert tools.run_tool("get_weather", "not json", OWNER).startswith("Error running get_weather")
    assert tools.run_tool("get_weather", '{"town": "Pune"}', OWNER).startswith("Error running get_weather")


def test_remember_fact_uses_our_chat_id_not_the_models():
    tools.run_tool("remember_fact", '{"fact": "Loves cricket", "chat_id": 999}', OWNER)
    assert [fact for _, fact in memory.get_facts(OWNER)] == ["Loves cricket"]
    assert memory.get_facts(999) == []


def test_recall_facts_lists_ids():
    fact_id = memory.add_fact(OWNER, "Loves cricket")
    assert tools.run_tool("recall_facts", "{}", OWNER) == f"#{fact_id}: Loves cricket\n"


GOOGLE_CALLS = [
    ("get_events", '{"start_date": "2026-10-05", "end_date": "2026-10-05"}'),
    ("create_event", EVENT),
    ("search_emails", '{"query": "x"}'),
    ("read_email", '{"email_id": "x"}'),
    ("create_draft", '{"to": "a@b.c", "subject": "s", "body": "b"}'),
]


def test_google_tools_refuse_a_chat_with_no_linked_account():
    for name, arguments in GOOGLE_CALLS:
        assert tools.run_tool(name, arguments, FRIEND) == tools.NOT_CONNECTED


def test_the_owner_is_not_special_without_a_linked_account():
    """Access follows the linked account, not who owns the bot."""
    for name, arguments in GOOGLE_CALLS:
        assert tools.run_tool(name, arguments, OWNER) == tools.NOT_CONNECTED


def test_create_event_rejects_bad_times():
    tokens.save_token(OWNER, '{"token": "fake"}')
    assert tools.run_tool("create_event", '{"title": "Gym", "start": "tomorrow", "end": "2026-10-06T08:00"}', OWNER).startswith("Error")
    assert tools.run_tool("create_event", '{"title": "Gym", "start": "2026-10-06T08:00", "end": "2026-10-06T07:00"}', OWNER).startswith("Error")
    assert approvals.pending == {}


def test_create_event_only_proposes():
    tokens.save_token(OWNER, '{"token": "fake"}')
    result = tools.run_tool("create_event", EVENT, OWNER)
    assert result.startswith("NOT DONE YET")
    assert approvals.pending_description(OWNER) == "Create event 'Gym' on Tue 06 Oct, 07:00 AM - 08:00 AM"
    # chat_id travels with the stored action, so the event is created in the
    # right person's calendar when they approve.
    assert approvals.pending[OWNER]["args"] == {
        "chat_id": OWNER, "title": "Gym", "start": "2026-10-06T07:00", "end": "2026-10-06T08:00",
    }
