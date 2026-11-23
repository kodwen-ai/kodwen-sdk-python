"""Project-scoped coordination queue (agentq): ``/v1/agentq/queue`` and ``/v1/agentq/claim``.

The server-authoritative counterpart of the local ``agentq`` coordinator on an operator machine. A ticket
names one contended resource (``build:codai``, ``deploy:gateway``, …) inside a project, and a caller claims
the head of that queue when a slot is free.

    ``enqueue`` — ``POST /v1/agentq/queue`` — add one ticket (HTTP 201)
    ``claim``   — ``POST /v1/agentq/claim`` — admit a holder to the head (HTTP 200, also when nothing can be claimed)

Ordering is ``priority`` descending, then ``enqueued_at`` ascending, then ticket id. ``capacity`` is how many
holders a resource admits at once (default 1) and the effective value is the maximum over the resource's live
tickets. Both routes are scoped to a single project: a project the caller cannot see is answered ``404``
(never ``403``), so an id you do not own is indistinguishable from one that does not exist.

Each method returns the raw gateway payload:
``enqueue`` → ``{ok, ticket, admitted, holders, capacity, waiting}`` (201),
``claim`` → ``{ok, claimed, ticket, holders, capacity, waiting}`` (200)."""

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
