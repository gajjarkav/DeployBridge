# ------------------------------------------------------------------------------
# WHAT THIS IS
#   The 5 endpoints for /v1/deployments. There is NO create endpoint —
#   new rows are written by the EXISTING /render/deploy and
#   /github-pages/deploy handlers as a side-effect of the deploy call.
#   One user action = one atomic operation.
#
# ENDPOINTS
#   GET    /v1/deployments                  paginated list, current user
#   GET    /v1/deployments/{id}             one deployment's detail
#   POST   /v1/deployments/{id}/refresh     ← THE KEY ENDPOINT
#   POST   /v1/deployments/{id}/redeploy     proxy to platform
#   DELETE /v1/deployments/{id}              remove from history
#
# WHY THIS SHAPE
#   Mirrors the pagination + try/except pattern in /reports.py exactly —
#   consistency = free marks.
# ------------------------------------------------------------------------------
import uuid
from typing import Awaitable

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.crypto import TokenDecryptionError
from ...core.exception import GitHubAPIError, RenderError
from ...db.session import get_db
from ...models.deployment import Deployment
from ...models.user import User
from ...schemas.deployment import (
    DeploymentDeleteResponse,
    DeploymentItem,
    DeploymentListResponse,
    DeploymentRefreshResponse,
    DeploymentRedeployResponse,
)
from ...services.deployment_service import DeploymentService, _row_to_item
from ..dependencies import get_current_user


router = APIRouter()


async def _resolve_deployment_or_404(
    db: AsyncSession, user: User, deployment_id: uuid.UUID
) -> Deployment:
    """Inline guard so each handler doesn't repeat the try/except + 404."""
    try:
        return await DeploymentService.get_one(db, user.id, deployment_id)
    except LookupError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found",
        ) from None


# ---------------------------------------------------------------------------
# List
# ---------------------------------------------------------------------------
@router.get(
    "",
    response_model=DeploymentListResponse,
    summary="List the current user's deployments (paginated)",
)
async def list_deployments(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns newest-first paginated deployments for the current user.

    Same pagination shape as GET /v1/reports/history so the frontend can
    reuse the exact same page/page_size/total handling.
    """
    return await DeploymentService.list_for_user(
        db, current_user.id, page=page, page_size=page_size
    )


# ---------------------------------------------------------------------------
# Detail
# ---------------------------------------------------------------------------
@router.get(
    "/{deployment_id}",
    response_model=DeploymentItem,
    summary="Get one deployment's full detail",
)
async def get_deployment(
    deployment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    deployment = await _resolve_deployment_or_404(db, current_user, deployment_id)
    return _row_to_item(deployment)


# ---------------------------------------------------------------------------
# Refresh — THE KEY ENDPOINT
# ---------------------------------------------------------------------------
@router.post(
    "/{deployment_id}/refresh",
    response_model=DeploymentRefreshResponse,
    summary="Pull the latest status from the upstream platform",
)
async def refresh_deployment(
    deployment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Hits the platform's status API (Render's get_service + get_deploy_logs,
    or GitHub's get_workflow_run_status) and updates the row.

    Pull-on-view model: the frontend calls this every 8-10s while any
    visible row is PENDING/BUILDING. Push/poller via APScheduler is a
    stretch goal — see IMPLEMENTATION_GUIDE.md.
    """
    deployment = await _resolve_deployment_or_404(db, current_user, deployment_id)
    try:
        result = await DeploymentService.refresh(db, current_user, deployment)
    except TokenDecryptionError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except (RenderError, GitHubAPIError) as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail or exc.message,
        ) from exc
    return result


# ---------------------------------------------------------------------------
# Redeploy
# ---------------------------------------------------------------------------
@router.post(
    "/{deployment_id}/redeploy",
    response_model=DeploymentRedeployResponse,
    summary="Trigger a new deploy on the upstream platform",
)
async def redeploy_deployment(
    deployment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Render:  POST /v1/services/{id}/deploys.
    Pages:    Re-dispatch the workflow on the recorded branch.

    Returns the new external_deploy_id (Render only — Pages' run id is
    discovered by the next /refresh call after GitHub Actions registers
    the new run).
    """
    deployment = await _resolve_deployment_or_404(db, current_user, deployment_id)
    try:
        return await DeploymentService.redeploy(db, current_user, deployment)
    except TokenDecryptionError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except (RenderError, GitHubAPIError) as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail or exc.message,
        ) from exc


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------
@router.delete(
    "/{deployment_id}",
    response_model=DeploymentDeleteResponse,
    summary="Remove a deployment from history",
)
async def delete_deployment(
    deployment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Removes the row from our DB. Does NOT touch the actual upstream
    Render service or GitHub Pages site — the deploy keeps running on
    the platform. Use this for cleanup of stale history entries."""
    deployment = await _resolve_deployment_or_404(db, current_user, deployment_id)
    str_id = str(deployment.id)
    await db.delete(deployment)
    await db.flush()
    return DeploymentDeleteResponse(
        success=True,
        id=str_id,
        message="Deployment removed from history.",
    )
