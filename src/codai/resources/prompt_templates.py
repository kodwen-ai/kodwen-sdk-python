"""Prompt templates: ``/v1/prompt-templates/*`` — your named, reusable prompts.

A template carries a ``kind`` (``agent_task`` — the default — for a task on a machine, ``session`` for a
chat turn, ``generic`` for anything else), optional ``repo`` / ``branch`` hints, ``tags`` and default
``variables`` for its ``{{name}}`` placeholders. Each row also has a ``body``, a name unique per account
and ``created_at`` / ``updated_at`` (typed in ``codai._types.PromptTemplate``).

``instantiate`` expands a template: every ``{{name}}`` placeholder is replaced from ``vars``, falling back
to the template's own ``variables``; a placeholder with no value is left exactly as written, so the caller
can still fill it in by hand.

Each method returns the raw gateway payload: ``list`` → ``{"data": [...], "next_cursor": ...}``,
``create`` / ``get`` / ``update`` → one ``PromptTemplate``, ``delete`` → ``{"deleted": 0|1}``,
``instantiate`` → ``{"prompt": str}``."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .._http import RequestExtensions
from ._base import Resource, enc

__all__ = ["PromptTemplates"]


def _templates(template_id: str, suffix: str = "") -> str:
    return f"/v1/prompt-templates/{enc(template_id)}{suffix}"


def _ext(ext: Optional[RequestExtensions], request_id: Optional[str]) -> Optional[RequestExtensions]:
    """Fold an explicit ``request_id`` into the ``X-Codai-*`` extension bag.

    ``request_id`` is the spec's ``x-request-id`` header (a client correlation id, echoed back as
    ``x-codai-trace-id`` and persisted on the usage row). An explicit ``request_id`` wins over one already
    inside ``ext``."""
    if not request_id:
        return ext
    merged: Dict[str, Any] = dict(ext or {})
    merged["request_id"] = request_id
    return merged


class PromptTemplates(Resource):
    def list(
        self,
        *,
        kind: Optional[str] = None,
        tag: Optional[str] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        request_id: Optional[str] = None,
        ext: Optional[RequestExtensions] = None,
    ) -> Dict[str, Any]:
        """``GET /v1/prompt-templates`` — your templates, newest first (``listPromptTemplates``).

        ``kind`` (``agent_task`` | ``session`` | ``generic``) and ``tag`` combine with AND; ``limit``
        (1–200) plus the opaque ``next_cursor`` from a previous page give keyset pagination. Returns
        ``{"data": [PromptTemplate], "next_cursor": str | None}``. Raises 402 while the wallet is empty."""
        return self._json(
            "/v1/prompt-templates",
            ext=_ext(ext, request_id),
            query={"kind": kind, "tag": tag, "limit": limit, "cursor": cursor},
        )

    def create(
        self,
        body: Dict[str, Any],
        *,
        request_id: Optional[str] = None,
        ext: Optional[RequestExtensions] = None,
    ) -> Dict[str, Any]:
        """``POST /v1/prompt-templates`` — save a named prompt (``createPromptTemplate``).

        ``body`` is ``codai._types.PromptTemplateCreate`` (``name`` and ``body`` required; optional ``kind``,
        ``repo``, ``branch``, ``tags``, ``variables``). The name is unique per account: reusing one is 409
        ``prompt_template_name_taken``. Returns the created ``PromptTemplate`` (201)."""
        return self._json("/v1/prompt-templates", ext=_ext(ext, request_id), method="POST", body=body)

    def get(
        self,
        template_id: str,
        *,
        request_id: Optional[str] = None,
        ext: Optional[RequestExtensions] = None,
    ) -> Dict[str, Any]:
        """``GET /v1/prompt-templates/{id}`` — one template, including its body and default variables
        (``getPromptTemplate``). A foreign or malformed id is 404."""
        return self._json(_templates(template_id), ext=_ext(ext, request_id))

    def update(
        self,
        template_id: str,
        body: Dict[str, Any],
        *,
        request_id: Optional[str] = None,
        ext: Optional[RequestExtensions] = None,
    ) -> Dict[str, Any]:
        """``PATCH /v1/prompt-templates/{id}`` — change any subset of the fields, at least one
        (``updatePromptTemplate``); ``body`` is ``codai._types.PromptTemplatePatch``. Renaming onto a name
        another of your templates already uses is 409. Returns the updated ``PromptTemplate``."""
        return self._json(_templates(template_id), ext=_ext(ext, request_id), method="PATCH", body=body)

    def delete(
        self,
        template_id: str,
        *,
        request_id: Optional[str] = None,
        ext: Optional[RequestExtensions] = None,
    ) -> Dict[str, Any]:
        """``DELETE /v1/prompt-templates/{id}`` — delete one of your templates
        (``deletePromptTemplate``). Unknown, malformed or foreign ids are not an error: the response is
        200 with ``{"deleted": 0}`` (or ``{"deleted": 1}`` when one was removed)."""
        return self._json(_templates(template_id), ext=_ext(ext, request_id), method="DELETE")

    def instantiate(
        self,
        template_id: str,
        body: Optional[Dict[str, Any]] = None,
        *,
        request_id: Optional[str] = None,
        ext: Optional[RequestExtensions] = None,
    ) -> Dict[str, Any]:
        """``POST /v1/prompt-templates/{id}/instantiate`` — expand a template
        (``instantiatePromptTemplate``).

        ``body`` is ``codai._types.PromptTemplateInstantiate`` (optional ``vars``: values for the
        ``{{name}}`` placeholders, overriding the template defaults). Returns ``{"prompt": str}`` with every
        placeholder that had a value replaced; a placeholder without one is left as written."""
        return self._json(
            _templates(template_id, "/instantiate"),
            ext=_ext(ext, request_id),
            method="POST",
            body=body or {},
        )
