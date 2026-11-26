"""Project health registry: ``/v1/platform/projects/*`` — read-only, needs a key scoped ``projects:read``."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .._http import RequestExtensions
from ._base import Resource, enc, list_of

__all__ = ["PlatformProjects"]


class PlatformProjects(Resource):
    def list(self, ext: Optional[RequestExtensions] = None) -> List[Dict[str, Any]]:
        """``GET /v1/platform/projects`` — the public projects plus the ones you own, with their roll-up."""
        return list_of(self._json("/v1/platform/projects", ext=ext), "projects")

    def get(self, id_or_slug: str, ext: Optional[RequestExtensions] = None) -> Dict[str, Any]:
        """``GET /v1/platform/projects/{id}`` — one project with its components; 404 when it is not yours to see."""
        return self._json(f"/v1/platform/projects/{enc(id_or_slug)}", ext=ext) or {}

    def status(self, id_or_slug: str, ext: Optional[RequestExtensions] = None) -> Dict[str, Any]:
        """``GET /v1/platform/projects/{id}/status`` — the roll-up a monitor polls, with ``checked_at`` per component."""
        return self._json(f"/v1/platform/projects/{enc(id_or_slug)}/status", ext=ext) or {}

    def incidents(
        self, id_or_slug: str, status: Optional[str] = None, ext: Optional[RequestExtensions] = None
    ) -> Dict[str, Any]:
        """``GET /v1/platform/projects/{id}/incidents`` — open incidents unless ``status`` is ``resolved``/``all``."""
        return self._json(
            f"/v1/platform/projects/{enc(id_or_slug)}/incidents", ext=ext, query={"status": status}
        ) or {}
