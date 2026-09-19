
# ------------------------------------------------------------------------------
# WHAT THIS IS
#   Pydantic request/response schemas for the /v1/deployments endpoints.
#
# DESIGN
#   Mirrors the shape of schemas/reports.py — one response model for the
#   paginated list (with `items` + `total` + `page` + `page_size`) and one
#   for single-row detail. The frontend's deployments.js can reuse the exact
#   same pagination pattern reports.js already uses, for free.
#
#   There is NO `DeploymentCreateRequest`. New rows are written by the
#   existing /v1/render/deploy and /v1/github-pages/deploy handlers as a
#   side-effect of the deploy call. One user action = one atomic operation;
#   no orphan rows, no "deploy happened but history forgot".
# ------------------------------------------------------------------------------

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


DeploymentPlatform = Literal["github_pages", "render"]
DeploymentStatus = Literal["pending", "building", "live", "failed"]


class DeploymentItem(BaseModel):
    """
    One row in the deployments list.

    Returned by GET /v1/deployments (inside DeploymentListResponse.items)
    and by GET /v1/deployments/{id}.
    """
    id: str = Field(..., description="UUID")
    platform: DeploymentPlatform
    owner: str
    repo: str
    branch: str
    profile: str | None = None
    status: DeploymentStatus
    service_id: str | None = None
    external_deploy_id: str | None = None
    url: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class DeploymentListResponse(BaseModel):
    """Paginated list response — same shape as ReportHistoryResponse."""
    items: list[DeploymentItem]
    total: int
    page: int
    page_size: int


class DeploymentRefreshResponse(DeploymentItem):
    """Returned by POST /v1/deployments/{id}/refresh.

    The endpoint hits the upstream platform's status API, updates the row,
    and returns the fresh row. Same shape as DeploymentItem — the wrapper
    subclass exists so the OpenAPI docs say 'refresh' not 'item', which
    makes the frontend code easier to read.
    """
    refreshed: bool = Field(
        default=True,
        description="True when the row was actually updated; False when "
                    "the platform call was skipped (e.g. already terminal).",
    )


class DeploymentRedeployResponse(BaseModel):
    """Returned by POST /v1/deployments/{id}/redeploy.

    Proxies to the platform's redeploy API. For Render, that's
    POST /v1/services/{id}/deploys. For Pages, we re-dispatch the
    workflow — Pages has no concept of "redeploy an old run", so we
    re-trigger the workflow run on the same branch/profile.
    """
    success: bool
    deployment_id: str
    new_external_deploy_id: str | None = None
    message: str


class DeploymentDeleteResponse(BaseModel):
    success: bool
    id: str
    message: str