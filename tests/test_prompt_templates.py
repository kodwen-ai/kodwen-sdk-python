"""``client.prompt_templates`` against the stdlib ``http.server`` stub (no network).

Covers the six ``/v1/prompt-templates`` operations: method, path, query, body, the parsed result and
the ``x-request-id`` header (from the explicit ``request_id=`` kwarg and from the house-style ``ext`` bag).
"""

from __future__ import annotations

import urllib.parse

TID = "11111111-1111-1111-1111-111111111111"
TEMPLATE = {
    "id": TID,
    "name": "ship it",
    "body": "Ship {{what}} please",
    "kind": "agent_task",
    "repo": None,
    "branch": None,
    "tags": ["ops"],
    "variables": {"what": "the build"},
    "created_at": "2026-11-22T00:00:00Z",
    "updated_at": "2026-11-22T00:00:00Z",
}


def test_prompt_templates_list_filters_and_pagination(client, stub):
    stub.reply(200, {"data": [TEMPLATE], "next_cursor": "c2"})
    payload = client.prompt_templates.list(kind="agent_task", tag="Ops", limit=25, cursor="c1")
    assert payload == {"data": [TEMPLATE], "next_cursor": "c2"}
    assert (stub.last.method, stub.last.path) == ("GET", "/v1/prompt-templates")
    assert urllib.parse.parse_qs(stub.last.query) == {
        "kind": ["agent_task"],
        "tag": ["Ops"],
        "limit": ["25"],
        "cursor": ["c1"],
    }

    # No filters → no query string at all.
    stub.reply(200, {"data": [], "next_cursor": None})
    assert client.prompt_templates.list() == {"data": [], "next_cursor": None}
    assert stub.last.query == ""


def test_prompt_templates_create_get_update_delete(client, stub):
    body = {
        "name": "ship it",
        "body": "Ship {{what}}",
        "kind": "session",
        "tags": ["ops"],
        "variables": {"what": "x"},
    }
    stub.reply(201, TEMPLATE)
    assert client.prompt_templates.create(body) == TEMPLATE
    assert (stub.last.method, stub.last.path, stub.last.json) == ("POST", "/v1/prompt-templates", body)

    stub.reply(200, TEMPLATE)
    assert client.prompt_templates.get(TID) == TEMPLATE
    assert (stub.last.method, stub.last.path) == ("GET", f"/v1/prompt-templates/{TID}")

    stub.reply(200, {**TEMPLATE, "name": "renamed"})
    assert client.prompt_templates.update(TID, {"name": "renamed"})["name"] == "renamed"
    assert (stub.last.method, stub.last.path, stub.last.json) == (
        "PATCH",
        f"/v1/prompt-templates/{TID}",
        {"name": "renamed"},
    )

    # delete() is a plain 200 both ways: {"deleted": 1} removed, {"deleted": 0} for an unknown / foreign id.
    stub.reply(200, {"deleted": 1})
    assert client.prompt_templates.delete(TID) == {"deleted": 1}
    assert (stub.last.method, stub.last.path) == ("DELETE", f"/v1/prompt-templates/{TID}")
    stub.reply(200, {"deleted": 0})
    assert client.prompt_templates.delete("nope") == {"deleted": 0}
    assert stub.last.path == "/v1/prompt-templates/nope"


def test_prompt_templates_instantiate_vars_and_defaults(client, stub):
    stub.reply(200, {"prompt": "Ship the release"})
    assert client.prompt_templates.instantiate(TID, {"vars": {"what": "the release"}}) == {
        "prompt": "Ship the release"
    }
    assert (stub.last.method, stub.last.path) == ("POST", f"/v1/prompt-templates/{TID}/instantiate")
    assert stub.last.json == {"vars": {"what": "the release"}}

    # body is optional: an empty JSON body lets the template's own `variables` fill the placeholders.
    stub.reply(200, {"prompt": "Ship {{what}}"})
    assert client.prompt_templates.instantiate(TID) == {"prompt": "Ship {{what}}"}
    assert stub.last.json == {}


def test_prompt_templates_request_id_header(client, stub):
    stub.reply(200, {"data": [], "next_cursor": None})
    client.prompt_templates.list(request_id="corr-1")
    assert stub.last.headers["x-request-id"] == "corr-1"

    stub.reply(200, TEMPLATE)
    client.prompt_templates.get(TID, request_id="corr-2")
    assert stub.last.headers["x-request-id"] == "corr-2"

    # ...and through the house-style ext bag for method-specific options.
    stub.reply(200, {"deleted": 0})
    client.prompt_templates.delete(TID, ext={"request_id": "corr-3"})
    assert stub.last.headers["x-request-id"] == "corr-3"


def test_prompt_templates_encodes_the_id(client, stub):
    stub.reply(200, TEMPLATE)
    client.prompt_templates.get("a b/c")
    assert stub.last.path == "/v1/prompt-templates/a%20b%2Fc"
