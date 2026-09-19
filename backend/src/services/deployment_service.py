# ------------------------------------------------------------------------------
# WHAT THIS IS
#   Service layer between the API endpoints (/v1/deployments) and the
#   platform services (RenderService, GitHubService).
#
# WHAT IT DOES
#   - create_from_pages_deploy / create_from_render_deploy:
#       Called by the EXISTING /render/deploy and /github-pages/deploy
#       handlers so every user action becomes one row in PostgreSQL.
#       No new POST /deployments create endpoint — one user action =
#       one atomic operation.
#
#   - refresh:
#       THE KEY METHOD. Hits the upstream platform's status API
#       (Render's get_service + get_deploy_logs, or GitHub's
#       get_workflow_run_status) and updates the row. Pull-on-view:
#       the frontend asks /refresh while the Deployments page is open.
#       Simple, zero background infra. Push/poller via APScheduler is a
#       stretch goal documented in IMPLEMENTATION_GUIDE.md.
#
#   - redeploy:
#       Proxies to the platform's redeploy API. For Render that's
#       POST /v1/services/{id}/deploys; for Pages we re-dispatch the
#       workflow file recorded in the row's service_id column.
#
# WHY A SERVICE LAYER
#   The api/v1/deployments.py handlers stay thin (auth, db session,
#   Pydantic shapes). This module owns the messy upstream API mapping
#   so it can be tested / mocked without spinning up FastAPI.
# ------------------------------------------------------------------------------
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.crypto import TokenDecryptionError, decrypt_secret
from ..core.exception import GitHubAPIError, GitHubPagesError, RenderError
from ..core.logger import logger
from ..models.deployment import Deployment
from ..models.user import User
from ..schemas.deployment import (
    DeploymentItem,
    DeploymentListResponse,
    DeploymentRefreshResponse,
    DeploymentRedeployResponse,
)
from .github import GitHubService
from .github_pages import GitHubPagesService
from .render import RenderService


# ---------------------------------------------------------------------------
# Mapping helpers — turn platform-native status into our row status enum.
# ---------------------------------------------------------------------------

# Render deploy.status values, verified against the live Render API.
_RENDER_STATUS_TO_DB = {
    "created":         "building",
    "building":        "building",
    "build_in_progress": "building",
    "live":            "live",
    "update_in_progress": "building",
    "deactivated":     "failed",
    "build_failed":    "failed",
    "update_failed":   "failed",
    "canceled":        "failed",
    "cancelled":       "failed",
}

# GitHub Actions run.status / run.conclusion → our row status.
_PAGES_STATUS_TO_DB = {
    # status field
    "queued":       "building",
    "in_progress":  "building",
    "waiting":      "building",
    # conclusion field (status == "completed")
    "success":      "live",
    "failure":      "failed",
    "cancelled":    "failed",
    "startup_failure": "failed",
    "timed_out":    "failed",
    "action_required": "failed",
    "neutral":      "failed",
}


def _map_render_status(deploy_status: str | None) -> str:
    if not deploy_status:
        return "building"
    return _RENDER_STATUS_TO_DB.get(deploy_status, "building")


def _map_pages_status(run_status: str | None, conclusion: str | None) -> str:
    """GitHub Actions: status is the lifecycle ('in_progress'), conclusion
    is the outcome ('success'/'failure') — only present when status=='completed'.
    """
    if run_status == "completed" and conclusion:
        return _PAGES_STATUS_TO_DB.get(conclusion, "failed")
    if run_status:
        return _PAGES_STATUS_TO_DB.get(run_status, "building")
    return "building"


def _row_to_item(d: Deployment) -> DeploymentItem:
    """ORM row → Pydantic item (used by every endpoint)."""
    return DeploymentItem(
        id=str(d.id),
        platform=d.platform,  # type: ignore[arg-type]
        owner=d.owner,
        repo=d.repo,
        branch=d.branch,
        profile=d.profile,
        status=d.status,  # type: ignore[arg-type]
        service_id=d.service_id,
        external_deploy_id=d.external_deploy_id,
        url=d.url,
        error=d.error,
        created_at=d.created_at,
        updated_at=d.updated_at,
    )


class DeploymentService:
    """Thin orchestration layer over RenderService / GitHubService."""

    # ------------------------------------------------------------------
    # Row creation hooks (called by render/deploy & github-pages/deploy)
    # ------------------------------------------------------------------
    @classmethod
    async def create_from_pages_deploy(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        *,
        owner: str,
        repo: str,
        branch: str,
        profile: str,
        workflow_filename: str,
    ) -> Deployment:
        """Insert a PENDING row right before returning the deploy response.

        Called inside the existing /github-pages/deploy handler. The row's
        status starts as `pending` and the frontend will flip it to
        `building`/`live`/`failed` by calling /refresh after the workflow
        has had time to register with GitHub Actions.
        """
        deployment = Deployment(
            user_id=user_id,
            platform="github_pages",
            owner=owner,
            repo=repo,
            branch=branch,
            profile=profile,
            status="pending",
            service_id=workflow_filename,  # the .yml filename
        )
        db.add(deployment)
        await db.flush()  # populate .id without committing yet
        return deployment

    @classmethod
    async def create_from_render_deploy(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        *,
        owner: str,
        repo: str,
        branch: str,
        runtime: str,
        service_id: str,
        deploy_id: str,
        service_url: str | None,
    ) -> Deployment:
        """Insert a BUILDING row immediately after Render's POST /services
        returns. Render kicks off the build the instant the service is
        created, so we can skip PENDING here — straight to BUILDING."""
        deployment = Deployment(
            user_id=user_id,
            platform="render",
            owner=owner,
            repo=repo,
            branch=branch,
            profile=runtime,
            status="building",
            service_id=service_id,
            external_deploy_id=deploy_id,
            url=service_url,
        )
        db.add(deployment)
        await db.flush()
        return deployment

    # ------------------------------------------------------------------
    # List / detail / delete
    # ------------------------------------------------------------------
    @classmethod
    async def list_for_user(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        *,
        page: int = 1,
        page_size: int = 10,
    ) -> DeploymentListResponse:
        """Paginated list, newest first. Same pagination shape as
        ReportHistoryResponse so the frontend can reuse the same code."""
        offset = (page - 1) * page_size

        count_stmt = select(func.count(Deployment.id)).where(
            Deployment.user_id == user_id
        )
        total = (await db.execute(count_stmt)).scalar_one()

        stmt = (
            select(Deployment)
            .where(Deployment.user_id == user_id)
            .order_by(desc(Deployment.created_at))
            .offset(offset)
            .limit(page_size)
        )
        rows = (await db.execute(stmt)).scalars().all()

        return DeploymentListResponse(
            items=[_row_to_item(r) for r in rows],
            total=total or 0,
            page=page,
            page_size=page_size,
        )

    @classmethod
    async def get_one(
        cls,
        db: AsyncSession,
        user_id: uuid.UUID,
        deployment_id: uuid.UUID,
    ) -> Deployment:
        stmt = select(Deployment).where(
            Deployment.id == deployment_id,
            Deployment.user_id == user_id,
        )
        row = (await db.execute(stmt)).scalars().first()
        if row is None:
            raise LookupError("Deployment not found")
        return row

    # ------------------------------------------------------------------
    # REFRESH — THE KEY METHOD
    # ------------------------------------------------------------------
    @classmethod
    async def refresh(
        cls,
        db: AsyncSession,
        user: User,
        deployment: Deployment,
    ) -> DeploymentRefreshResponse:
        """Pull the latest status from the upstream platform and update
        the row. Pull-on-view model: the frontend asks /refresh while
        the Deployments page is open.

        Terminal rows (LIVE / FAILED) are skipped — refreshing them is
        wasted work and would hammer the platform API. The frontend
        should stop polling once every visible row is terminal.
        """
        if deployment.status in ("live", "failed"):
            return DeploymentRefreshResponse(
                **_row_to_item(deployment).model_dump(),
                refreshed=False,
            )

        if deployment.platform == "render":
            await cls._refresh_render(db, user, deployment)
        elif deployment.platform == "github_pages":
            await cls._refresh_pages(db, user, deployment)
        else:
            raise ValueError(f"Unknown platform: {deployment.platform}")

        await db.flush()
        return DeploymentRefreshResponse(
            **_row_to_item(deployment).model_dump(),
            refreshed=True,
        )

    @classmethod
    async def _refresh_render(
        cls,
        db: AsyncSession,
        user: User,
        deployment: Deployment,
    ) -> None:
        if not user.render_api_key or not deployment.service_id:
            deployment.status = "failed"
            deployment.error = "Render API key disconnected or service_id missing."
            return

        try:
            api_key = decrypt_secret(user.render_api_key)
        except TokenDecryptionError as exc:
            deployment.status = "failed"
            deployment.error = f"Could not decrypt Render API key: {exc}"
            return

        try:
            detail = await RenderService.get_service(
                api_key=api_key,
                service_id=deployment.service_id,
            )
        except RenderError as exc:
            deployment.status = "failed"
            deployment.error = f"{exc.message}: {exc.detail}"[:4000]
            return

        new_status = _map_render_status(detail.latest_deploy_status)

        # Update URL if Render has assigned/changed it.
        if detail.url:
            deployment.url = detail.url

        # Capture deploy_id if we didn't have it before (Pages path) —
        # Render rows already have it from create, but a redeploy produces
        # a new deploy_id we want to track.
        if detail.latest_deploy_id and detail.latest_deploy_id != deployment.external_deploy_id:
            deployment.external_deploy_id = detail.latest_deploy_id

        if new_status == "failed":
            # Pull the build log so the row's `error` carries the actual
            # traceback Render surfaced. The agent uses this in Flow B.
            if detail.latest_deploy_id:
                try:
                    logs = await RenderService.get_deploy_logs(
                        api_key=api_key,
                        service_id=deployment.service_id,
                        deploy_id=detail.latest_deploy_id,
                        limit=200,
                    )
                    deployment.error = logs or "Build failed — Render did not return logs."
                except RenderError as exc:
                    deployment.error = f"Build failed. Logs fetch failed: {exc.message}"
            else:
                deployment.error = "Build failed — no deploy id available."

        deployment.status = new_status

    @classmethod
    async def _refresh_pages(
        cls,
        db: AsyncSession,
        user: User,
        deployment: Deployment,
    ) -> None:
        if not user.github_token:
            deployment.status = "failed"
            deployment.error = "GitHub token missing. Re-authenticate."
            return

        try:
            github_token = decrypt_secret(user.github_token)
        except TokenDecryptionError as exc:
            deployment.status = "failed"
            deployment.error = f"Could not decrypt GitHub token: {exc}"
            return

        # external_deploy_id holds the workflow run id (numeric, as int-as-str)
        run_id: int | None = None
        if deployment.external_deploy_id:
            try:
                run_id = int(deployment.external_deploy_id)
            except (TypeError, ValueError):
                run_id = None

        try:
            run = await GitHubService.get_workflow_run_status(
                token=github_token,
                owner=deployment.owner,
                repo=deployment.repo,
                branch=deployment.branch,
                workflow_filename=deployment.service_id or None,
                run_id=run_id,
            )
        except Exception as exc:
            deployment.status = "failed"
            deployment.error = f"GitHub Actions API error: {exc}"[:4000]
            return

        if not run:
            # No run found yet — workflow was just dispatched, GitHub Actions
            # hasn't registered it. Leave as pending/building; the frontend
            # will retry on its 8s interval.
            if deployment.status == "pending":
                deployment.status = "building"
            return

        # Cache the run_id so subsequent /refresh calls hit /runs/{id} directly
        # (saves the wider /actions/runs scan).
        if run.get("run_id") and str(run["run_id"]) != deployment.external_deploy_id:
            deployment.external_deploy_id = str(run["run_id"])

        new_status = _map_pages_status(run.get("status"), run.get("conclusion"))

        if new_status == "live" and not deployment.url:
            # Construct the canonical Pages URL — we don't actually fetch the
            # /pages endpoint (the old frontend did that; the backend refresh
            # path keeps it simple and trusts the convention).
            deployment.url = (
                f"https://{deployment.owner}.github.io/{deployment.repo}".rstrip("/")
            )

        if new_status == "failed" and run.get("run_id"):
            try:
                logs = await GitHubService.get_workflow_run_logs(
                    token=github_token,
                    owner=deployment.owner,
                    repo=deployment.repo,
                    run_id=int(run["run_id"]),
                )
                deployment.error = logs or "Workflow failed — no logs available."
            except Exception:
                deployment.error = "Workflow failed — logs fetch failed."

        deployment.status = new_status

    # ------------------------------------------------------------------
    # REDEPLOY
    # ------------------------------------------------------------------
    @classmethod
    async def redeploy(
        cls,
        db: AsyncSession,
        user: User,
        deployment: Deployment,
    ) -> DeploymentRedeployResponse:
        """Trigger a new deploy on the upstream platform.

        Render:  POST /v1/services/{id}/deploys — Render kicks off a fresh
                 build immediately and we get back a new deployId to track.
        Pages:   Re-dispatch the workflow via /actions/workflows/{file}/dispatches.
                 GitHub Actions will create a new run; the next /refresh
                 will discover it by post-filtering on workflow path.
        """
        if deployment.platform == "render":
            return await cls._redeploy_render(db, user, deployment)
        if deployment.platform == "github_pages":
            return await cls._redeploy_pages(db, user, deployment)
        raise ValueError(f"Unknown platform: {deployment.platform}")

    @classmethod
    async def _redeploy_render(
        cls,
        db: AsyncSession,
        user: User,
        deployment: Deployment,
    ) -> DeploymentRedeployResponse:
        if not user.render_api_key or not deployment.service_id:
            raise RenderError(
                message="Cannot redeploy — Render integration disconnected.",
                detail="Re-connect Render in Settings.",
                status_code=400,
            )
        api_key = decrypt_secret(user.render_api_key)
        new_deploy_id = await RenderService.trigger_deploy(
            api_key=api_key,
            service_id=deployment.service_id,
            clear_cache=False,
        )
        # Reset the row to BUILDING so the frontend's auto-refresh kicks in.
        deployment.status = "building"
        deployment.external_deploy_id = new_deploy_id
        deployment.error = None
        await db.flush()
        return DeploymentRedeployResponse(
            success=True,
            deployment_id=str(deployment.id),
            new_external_deploy_id=new_deploy_id,
            message=f"Render redeploy triggered (deploy id {new_deploy_id}).",
        )

    @classmethod
    async def _redeploy_pages(
        cls,
        db: AsyncSession,
        user: User,
        deployment: Deployment,
    ) -> DeploymentRedeployResponse:
        if not user.github_token:
            raise GitHubAPIError(
                message="Cannot redeploy — GitHub token missing.",
                detail="Re-authenticate via GitHub OAuth.",
            )
        if not deployment.service_id:
            raise GitHubAPIError(
                message="Cannot redeploy — workflow filename not recorded on the row.",
            )
        github_token = decrypt_secret(user.github_token)

        # Re-dispatch the workflow file recorded on the row. We use the
        # same private method GitHubPagesService.deploy uses; this is one
        # reason that method exists as a separate unit.
        workflow_filename = deployment.service_id
        # Strip directory prefix if present — _dispatch_workflow takes the bare filename.
        if workflow_filename.startswith(".github/workflows/"):
            workflow_filename = workflow_filename[len(".github/workflows/"):]

        try:
            await GitHubPagesService._dispatch_workflow(
                github_token=github_token,
                owner=deployment.owner,
                repository=deployment.repo,
                target_branch=deployment.branch,
                workflow_filename=workflow_filename,
            )
        except GitHubPagesError as exc:
            raise RenderError(
                message=exc.message, detail=exc.detail, status_code=exc.status_code
            ) from exc

        deployment.status = "building"
        deployment.external_deploy_id = None  # next refresh will re-pick it up
        deployment.error = None
        await db.flush()
        return DeploymentRedeployResponse(
            success=True,
            deployment_id=str(deployment.id),
            new_external_deploy_id=None,
            message=f"Pages workflow {workflow_filename} re-dispatched on branch {deployment.branch}.",
        )