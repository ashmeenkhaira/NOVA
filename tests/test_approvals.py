import approvals
from conftest import FRIEND, OWNER


def make_action():
    ran = []

    def action(title):
        ran.append(title)
        return f"created {title}"

    return action, ran


def test_nothing_waiting_means_normal_handling():
    assert approvals.handle_reply(OWNER, "yes") is None
    assert approvals.approval_prompt(OWNER) == ""


def test_yes_runs_exactly_once():
    action, ran = make_action()
    approvals.propose(OWNER, "Create 'Gym'", action, title="Gym")
    assert "Waiting for approval: Create 'Gym'" in approvals.approval_prompt(OWNER)
    assert approvals.handle_reply(OWNER, " Yes ") == "Done: created Gym"
    assert approvals.handle_reply(OWNER, "yes") is None
    assert ran == ["Gym"]


def test_anything_else_cancels():
    action, ran = make_action()
    approvals.propose(OWNER, "Create 'Gym'", action, title="Gym")
    assert approvals.handle_reply(OWNER, "yes but at 8") == "Cancelled. Nothing was done."
    assert ran == []


def test_other_chats_cannot_approve():
    action, ran = make_action()
    approvals.propose(OWNER, "Create 'Gym'", action, title="Gym")
    assert approvals.handle_reply(FRIEND, "yes") is None
    assert ran == []
    assert approvals.pending_description(OWNER) == "Create 'Gym'"


def test_failure_is_reported_not_raised():
    def broken():
        raise RuntimeError("Google said no")

    approvals.propose(OWNER, "Broken", broken)
    assert approvals.handle_reply(OWNER, "yes") == "Approved, but it failed: Google said no"
