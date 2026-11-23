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
