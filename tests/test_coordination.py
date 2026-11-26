"""Project-scoped coordination queue (agentq) against the http.server stub."""

from __future__ import annotations

_PROJECT = "2b6d1c0e-4f3a-4b9c-8d7e-1a2b3c4d5e6f"
_TICKET = {
    "id": "tkt-1",
    "project_id": _PROJECT,
    "resource": "build:codai",
    "state": "queued",
    "priority": 0,
    "capacity": 1,
    "holder": "",
    "session": "",
    "purpose": "",
    "cmd": "",
    "lane": "gate",
}


def test_enqueue_posts_the_ticket(client, stub):
    stub.reply(
        201,
        {"ok": True, "ticket": _TICKET, "admitted": True, "holders": 0, "capacity": 1, "waiting": 1},
    )
    r = client.coordination.enqueue({"project_id": _PROJECT, "resource": "build:codai", "priority": 3})
    assert r["ok"] is True and r["admitted"] is True
    assert r["ticket"]["id"] == "tkt-1" and r["waiting"] == 1
    assert [(q.method, q.path) for q in stub.requests] == [("POST", "/v1/agentq/queue")]
    assert stub.last.json == {"project_id": _PROJECT, "resource": "build:codai", "priority": 3}


def test_enqueue_not_admitted_when_a_slot_is_taken(client, stub):
    stub.reply(
        201,
        {"ok": True, "ticket": _TICKET, "admitted": False, "holders": 1, "capacity": 1, "waiting": 2},
    )
    r = client.coordination.enqueue({"project_id": _PROJECT, "resource": "build:codai"})
    assert r["admitted"] is False and r["holders"] == 1 and r["waiting"] == 2


def test_claim_returns_the_head_ticket(client, stub):
    claimed = {**_TICKET, "state": "claimed", "holder": "desktop-7f3a", "session": "s-9"}
    stub.reply(
        200,
        {"ok": True, "claimed": True, "ticket": claimed, "holders": 1, "capacity": 1, "waiting": 0},
    )
    r = client.coordination.claim({"project_id": _PROJECT, "resource": "build:codai", "holder": "desktop-7f3a"})
    assert r["claimed"] is True
    assert r["ticket"]["holder"] == "desktop-7f3a" and r["ticket"]["state"] == "claimed"
    assert [(q.method, q.path) for q in stub.requests] == [("POST", "/v1/agentq/claim")]
    assert stub.last.json == {
        "project_id": _PROJECT,
        "resource": "build:codai",
        "holder": "desktop-7f3a",
    }


def test_claim_polling_answer_is_not_an_error(client, stub):
    stub.reply(200, {"ok": True, "claimed": False, "ticket": None, "holders": 1, "capacity": 1, "waiting": 0})
    r = client.coordination.claim({"project_id": _PROJECT, "resource": "build:codai", "holder": "desktop-7f3a"})
    assert r["claimed"] is False and r["ticket"] is None and r["ok"] is True


def test_heartbeat_refreshes_the_holders_claimed_ticket(client, stub):
    claimed = {**_TICKET, "id": "tkt-9", "state": "claimed", "holder": "desktop-7f3a"}
    stub.reply(200, {"ok": True, "beaten": True, "ticket": claimed})
    body = {"project_id": _PROJECT, "resource": "build:codai", "ticket_id": "tkt-9", "holder": "desktop-7f3a"}
    r = client.coordination.heartbeat(body)
    assert r["beaten"] is True and r["ticket"]["state"] == "claimed"
    assert [(q.method, q.path) for q in stub.requests] == [("POST", "/v1/agentq/heartbeat")]
    assert stub.last.json == body


def test_heartbeat_no_op_is_not_an_error(client, stub):
    stub.reply(200, {"ok": True, "beaten": False, "ticket": None})
    body = {"project_id": _PROJECT, "resource": "build:codai", "ticket_id": "tkt-9", "holder": "ghost"}
    r = client.coordination.heartbeat(body)
    assert r["beaten"] is False and r["ticket"] is None and r["ok"] is True


def test_release_finishes_the_ticket_and_reports_the_freed_depth(client, stub):
    released = {**_TICKET, "id": "tkt-9", "state": "done", "holder": "desktop-7f3a"}
    stub.reply(200, {"ok": True, "released": True, "ticket": released, "holders": 0, "capacity": 1, "waiting": 0})
    r = client.coordination.release(
        {"project_id": _PROJECT, "resource": "build:codai", "ticket_id": "tkt-9", "holder": "desktop-7f3a"}
    )
    assert r["released"] is True and r["ticket"]["state"] == "done"
    assert r["holders"] == 0 and r["waiting"] == 0
    assert [(q.method, q.path) for q in stub.requests] == [("POST", "/v1/agentq/release")]
    # outcome is optional: it must not be invented client-side.
    assert stub.last.json == {
        "project_id": _PROJECT,
        "resource": "build:codai",
        "ticket_id": "tkt-9",
        "holder": "desktop-7f3a",
    }


def test_release_forwards_an_explicit_outcome(client, stub):
    stub.reply(200, {"ok": True, "released": True, "ticket": None, "holders": 0, "capacity": 1, "waiting": 0})
    r = client.coordination.release(
        {
            "project_id": _PROJECT,
            "resource": "build:codai",
            "ticket_id": "tkt-9",
            "holder": "desktop-7f3a",
            "outcome": "cancelled",
        }
    )
    assert r["released"] is True
    assert stub.last.json["outcome"] == "cancelled"
