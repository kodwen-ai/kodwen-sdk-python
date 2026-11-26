"""``/v1/lanes/publish`` — the dedicated-lane SKU's public edge (``publishLane``).

The gateway edge of the codai1 pool's own publish guard (``deploy/codai1-pool/lane_publish.py``): the pool is
the AUTHORITY on whether a token-rate lane MAY be sold and at what price, and this call only forwards the
question and returns the pool's answer. It never re-derives a price or a capacity.

    ``publish`` — ``POST /v1/lanes/publish`` — quote and publish a dedicated lane (HTTP 200)

A ``200`` is the pool's quote (``sellable: true``, with ``price_per_hour_eur`` / ``price_per_1m_output_eur``).
A refusal is never a ``200``: the pool's ``409`` is raised, and a malformed body is ``400``. The call is
read-only and idempotent — the same body always yields the same answer, so no ``Idempotency-Key``.

Error behaviour (from ``src/codai/_http.py``): the transport raises ``CodaiError`` on every non-2xx response —
``open`` retries only ``429`` / ``5xx`` and calls ``_to_error`` for anything else, so a ``409`` (not in the
retry set) is raised immediately, with the parsed gateway error envelope on ``CodaiError.body`` (the pool's
quote under ``error.details``). A ``409`` therefore raises rather than returning an unusable lane."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .._http import RequestExtensions
from ._base import Resource

__all__ = ["Lanes"]


class Lanes(Resource):
    """Quote and publish a dedicated token-rate lane through the codai1 pool."""

    def publish(self, body: Dict[str, Any], ext: Optional[RequestExtensions] = None) -> Dict[str, Any]:
        """``POST /v1/lanes/publish`` (``publishLane``) — ask the codai1 pool whether a token-rate lane may be
        published at ``lane_tokens_s`` on the given ``backing``, and return the pool's own quote (HTTP 200).

        ``body`` is ``{lane_tokens_s, backing, node_hourly_usd, margin, safety_factor?, nodes?, eur_per_usd?,
        overhead?}``; the optional knobs are forwarded unchanged, so the pool's own defaults stay authoritative.
        ``backing: dedicated`` is published when the lane's rate fits the exclusive capacity behind its nodes;
        ``backing: shared`` is refused (the shared pool carries an exclusive capacity of zero). The pool is the
        authority on price and capacity — this call only forwards the decision.

        200 is the pool's quote. **A 409 refusal raises** ``CodaiError`` (the pool's quote in
        ``error.details``); a malformed body is ``400``. Read-only and idempotent, so no ``Idempotency-Key``."""
        return self._json("/v1/lanes/publish", ext=ext, method="POST", body=body)
