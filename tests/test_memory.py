import memory
from conftest import FRIEND, OWNER


def test_add_and_get_facts():
    first = memory.add_fact(OWNER, "Loves cricket")
    second = memory.add_fact(OWNER, "Sister is called Priya")
    assert memory.get_facts(OWNER) == [(first, "Loves cricket"), (second, "Sister is called Priya")]


def test_facts_are_kept_per_chat():
    memory.add_fact(OWNER, "Lives in Delhi")
    memory.add_fact(FRIEND, "Likes chess")
    assert [fact for _, fact in memory.get_facts(OWNER)] == ["Lives in Delhi"]
    assert [fact for _, fact in memory.get_facts(FRIEND)] == ["Likes chess"]


def test_quotes_are_stored_safely():
    memory.add_fact(OWNER, "Shubham's team is RCB'); DROP TABLE memories; --")
    assert memory.get_facts(OWNER)[0][1] == "Shubham's team is RCB'); DROP TABLE memories; --"


def test_delete_only_own_fact():
    fact_id = memory.add_fact(OWNER, "Secret")
    assert memory.delete_fact(FRIEND, fact_id) is False   # someone else's fact
    assert memory.delete_fact(OWNER, fact_id) is True
    assert memory.delete_fact(OWNER, fact_id) is False    # already gone


def test_ids_are_never_reused():
    first = memory.add_fact(OWNER, "A")
    memory.delete_fact(OWNER, first)
    assert memory.add_fact(OWNER, "B") != first
