"""Durable agent teams per project (DSC-0066): one planner + N workers, each with its own worktree.

    ``list``        — ``GET   /v1/projects/{id}/teams``
    ``create``      — ``POST  /v1/projects/{id}/teams`` (HTTP 201)
    ``get``         — ``GET   /v1/agent-teams/{teamId}``
    ``bind_member`` — ``PATCH /v1/agent-teams/{teamId}/members/{memberId}``
    ``reconcile``   — ``POST  /v1/agent-teams/{teamId}/reconcile`` (409 while a worker is not terminal)
    ``cancel``      — ``POST  /v1/agent-teams/{teamId}/cancel`` (409 once the team has settled)

A team is a registry, not a second agent loop: creating one runs nothing. Bind each member to the cloud
session and environment task that executes it, then ``reconcile`` once every worker is terminal. A project
the caller cannot see is ``404``, never ``403``."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .._http import RequestExtensions
from ._base import Resource, enc, list_of

__all__ = ["AgentTeams"]


class AgentTeams(Resource):
    """Create, bind, reconcile and cancel a project's durable agent teams."""

    def list(self, project_id: str, ext: Optional[RequestExtensions] = None) -> List[Dict[str, Any]]:
        """``GET /v1/projects/{id}/teams`` (``listAgentTeams``) — the project's teams."""
        return list_of(self._json(f"/v1/projects/{enc(project_id)}/teams", ext=ext), "teams")

    def create(
        self, project_id: str, body: Dict[str, Any], ext: Optional[RequestExtensions] = None
    ) -> Dict[str, Any]:
        """``POST /v1/projects/{id}/teams`` (``createAgentTeam``) — ``{name, goal, environment_id?, workers}``
        → ``{team, members}`` (HTTP 201). Nothing runs yet; owner or org admin."""
        return self._json(f"/v1/projects/{enc(project_id)}/teams", ext=ext, method="POST", body=body)

    def get(self, team_id: str, ext: Optional[RequestExtensions] = None) -> Dict[str, Any]:
        """``GET /v1/agent-teams/{teamId}`` (``getAgentTeam``) — ``{team, members}``."""
        return self._json(f"/v1/agent-teams/{enc(team_id)}", ext=ext)

    def bind_member(
        self, team_id: str, member_id: str, body: Dict[str, Any], ext: Optional[RequestExtensions] = None
    ) -> Dict[str, Any]:
        """``PATCH /v1/agent-teams/{teamId}/members/{memberId}`` (``bindAgentTeamMember``) — bind a member to its
        session, task, branch or result; ``free_worktree: True`` releases its worktree. Returns the member."""
        raw = self._json(
            f"/v1/agent-teams/{enc(team_id)}/members/{enc(member_id)}", ext=ext, method="PATCH", body=body
        )
        return raw["member"]

    def reconcile(self, team_id: str, ext: Optional[RequestExtensions] = None) -> Dict[str, Any]:
        """``POST /v1/agent-teams/{teamId}/reconcile`` (``reconcileAgentTeam``) — fold the workers' results.
        Returns the team; ``409`` while any worker is pending."""
        return self._json(f"/v1/agent-teams/{enc(team_id)}/reconcile", ext=ext, method="POST")["team"]

    def cancel(self, team_id: str, ext: Optional[RequestExtensions] = None) -> Dict[str, Any]:
        """``POST /v1/agent-teams/{teamId}/cancel`` (``cancelAgentTeam``) — cancel a planning or running team.
        Returns the team; ``409`` once it has settled."""
        return self._json(f"/v1/agent-teams/{enc(team_id)}/cancel", ext=ext, method="POST")["team"]
