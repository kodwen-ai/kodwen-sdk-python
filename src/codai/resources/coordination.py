"""Project-scoped coordination queue (agentq): ``/v1/agentq/queue``, ``/claim``, ``/heartbeat``, ``/release``
and the owner's edit-ticket approvals (``/v1/agentq/approvals``).

The server-authoritative counterpart of the local ``agentq`` coordinator on an operator machine. A ticket
names one contended resource (``build:codai``, ``deploy:gateway``, …) inside a project, and a caller claims
the head of that queue when a slot is free.

    ``enqueue``   — ``POST /v1/agentq/queue`` — add one ticket (HTTP 201)
    ``claim``     — ``POST /v1/agentq/claim`` — admit a holder to the head (HTTP 200, also when nothing can be claimed)
    ``heartbeat`` — ``POST /v1/agentq/heartbeat`` — refresh ``beat_at`` on a claimed ticket (HTTP 200)
    ``release``   — ``POST /v1/agentq/release`` — finish a claimed ticket and free its slot (HTTP 200)
    ``list_approvals``   — ``GET /v1/agentq/approvals`` — list approvals (HTTP 200)
    ``decide_approval``  — ``POST /v1/agentq/approvals/{id}/decision`` — store a verdict (HTTP 200)

Ordering is ``priority`` descending, then ``enqueued_at`` ascending, then ticket id. ``capacity`` is how many
holders a resource admits at once (default 1) and the effective value is the maximum over the resource's live
tickets. Both routes are scoped to a single project: a project the caller cannot see is answered ``404``
(never ``403``), so an id you do not own is indistinguishable from one that does not exist.

Each method returns the raw gateway payload:
``enqueue`` → ``{ok, ticket, admitted, holders, capacity, waiting}`` (201),
``claim`` → ``{ok, claimed, ticket, holders, capacity, waiting}`` (200),
``heartbeat`` → ``{ok, beaten, ticket}`` (200),
``release`` → ``{ok, released, ticket, holders, capacity, waiting}`` (200),
``list_approvals`` → ``{ok, approvals}`` (200),
``decide_approval`` → ``{ok, approval}`` (200).

The two approval routes carry NO project scope: an edit ticket is decided by the OWNER on the owner's own
presence proof, and the verdict is only consent — the ticket's HMAC secret never leaves the machine that
asked for it."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .._http import RequestExtensions
from ._base import Resource

__all__ = ["Coordination"]


class Coordination(Resource):
    """Enqueue and claim tickets on a project's contended resources."""

    def enqueue(self, body: Dict[str, Any], ext: Optional[RequestExtensions] = None) -> Dict[str, Any]:
        """``POST /v1/agentq/queue`` (``enqueueAgentqTicket``) — add one ticket for ``resource`` to the project's
        queue and answer with the stored ticket plus the current depth (HTTP 201).

        ``body`` is ``{project_id, resource, lane?, priority?, capacity?, purpose?, cmd?, session?, holder?}``;
        ``project_id`` (uuid) and a non-empty ``resource`` are required, ``lane`` defaults to ``gate``,
        ``priority`` to ``0`` and ``capacity`` to ``1``. ``admitted: true`` means the ticket is the queue head
        and a slot is free, so the work can start immediately; otherwise poll :meth:`claim`. A project the
        caller cannot see is ``404``."""
        return self._json("/v1/agentq/queue", ext=ext, method="POST", body=body)

    def claim(self, body: Dict[str, Any], ext: Optional[RequestExtensions] = None) -> Dict[str, Any]:
        """``POST /v1/agentq/claim`` (``claimAgentqTicket``) — admit ``holder`` to ``resource`` when fewer than
        its capacity of tickets are already held (HTTP 200).

        ``body`` is ``{project_id, resource, holder, session?}``; ``holder`` names whoever is claiming so a stale
        claim stays attributable. Only the head of the queue can be taken, and the read-decide-write runs in one
        transaction locked to ``(project, resource)``, so two concurrent callers never receive the same slot.
        ``claimed: false`` with ``ticket: null`` means the queue is empty or every slot is taken — poll again
        rather than treating it as an error. A project the caller cannot see is ``404``."""
        return self._json("/v1/agentq/claim", ext=ext, method="POST", body=body)

    def heartbeat(self, body: Dict[str, Any], ext: Optional[RequestExtensions] = None) -> Dict[str, Any]:
        """``POST /v1/agentq/heartbeat`` (``heartbeatAgentqTicket``) — refresh ``beat_at`` on the caller's own
        claimed ticket so a long-running holder is not swept as stale (HTTP 200).

        ``body`` is ``{project_id, resource, ticket_id, holder}``. Only the ticket of that ``holder`` in state
        ``claimed`` is touched, and only its clock column: a heartbeat can never move a ticket's state or steal
        someone else's slot. ``beaten: false`` with ``ticket: null`` means there is nothing of this holder to
        refresh (already released, or another holder owns it) — not an error. A project the caller cannot see is
        ``404``."""
        return self._json("/v1/agentq/heartbeat", ext=ext, method="POST", body=body)

    def release(self, body: Dict[str, Any], ext: Optional[RequestExtensions] = None) -> Dict[str, Any]:
        """``POST /v1/agentq/release`` (``releaseAgentqTicket``) — finish the caller's claimed ticket, freeing
        its slot for the queue head (HTTP 200).

        ``body`` is ``{project_id, resource, ticket_id, holder, outcome?}``; ``outcome`` is ``done`` (default)
        or ``cancelled``. The state change runs under the same ``(project, resource)`` advisory lock as
        :meth:`claim`, so the returned ``holders`` / ``waiting`` reflect the queue immediately after the release.
        ``released: false`` with ``ticket: null`` means there was no claimed ticket of this holder to finish.
        A project the caller cannot see is ``404``."""
        return self._json("/v1/agentq/release", ext=ext, method="POST", body=body)

    def list_approvals(
        self, status: str = "pending", limit: Optional[int] = None, ext: Optional[RequestExtensions] = None
    ) -> Dict[str, Any]:
        """``GET /v1/agentq/approvals`` (``listAgentqApprovals``) — the owner's edit-ticket approvals (HTTP 200).

        ``status`` is ``pending`` (default, answered soonest-expiry first), ``approved``, ``denied``, ``expired``
        or ``all`` (decided and expired rows too, newest first); ``limit`` is clamped to the page ceiling of 200.
        The answer is ``{ok, approvals}``. Super-admin only: any other key gets ``403``."""
        query: Dict[str, Any] = {"status": status}
        if limit is not None:
            query["limit"] = limit
        return self._json("/v1/agentq/approvals", ext=ext, query=query) or {}

    def decide_approval(
        self, approval_id: int, decision: str, proof: Dict[str, Any], ext: Optional[RequestExtensions] = None
    ) -> Dict[str, Any]:
        """``POST /v1/agentq/approvals/{id}/decision`` (``decideAgentqApproval``) — record the owner's verdict on
        one request (HTTP 200).

        ``decision`` is ``approved`` or ``denied``, and ``proof`` is
        ``{kind: "biometric" | "webauthn", device_id?}``: it names the presence proof that authorised the verdict
        and is stored on the row as ``proof_kind``. The approval is only CONSENT — this route never mints or
        reveals the ticket's HMAC secret, which stays on the machine that asked for the ticket.

        A request cannot approve itself (``403`` ``self_approval`` when ``proof.device_id`` is the requesting
        host), an already-decided row is ``409`` ``not_pending``, an unknown id is ``404``, and a row past
        ``expires_at`` is ``410`` ``expired`` (and is marked as such) — a remote approval never outlives the
        request it answers. Super-admin only. The answer is ``{ok, approval}``."""
        return self._json(
            f"/v1/agentq/approvals/{int(approval_id)}/decision",
            ext=ext,
            method="POST",
            body={"decision": decision, "proof": proof},
        )
