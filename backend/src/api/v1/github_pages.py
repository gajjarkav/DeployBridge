from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.exception import GitHubPagesError
from ...db.session import get_db
from ...models.user import User
from ...schemas.github_pages import (
    GitHubPagesCustomDomainRequest,
    GitHubPagesCustomDomainResponse,
    GitHubPagesDeployRequest,
    GitHubPagesDeployResponse,
    GitHubPagesDetectResponse,
    GitHubPagesRepositoryRequest,
)
from ...services.deployment_service import DeploymentService
from ...services.github_pages import GitHubPagesService
from ..dependencies import get_current_user
from ...core.crypto import TokenDecryptionError, decrypt_secret


router = APIRouter()


def _require_github_token(current_user: User) -> str:
    """Common guard for every endpoint that calls GitHub on the user's behalf."""
    if not current_user.github_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your GitHub access token is missing from our records. Please re-authenticate.",
        )
    try:
        return decrypt_secret(current_user.github_token)
    except TokenDecryptionError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


@router.post(
    "/detect",
    response_model=GitHubPagesDetectResponse,
    summary="Detect GitHub Pages deployment profile",
)
async def detect_github_pages_profile(
    request: GitHubPagesRepositoryRequest,
    current_user: User = Depends(get_current_user)
):
    if not current_user.github_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your GitHub access token is missing from our records. Please re-authenticate.",
        )

    try:
        github_token = decrypt_secret(current_user.github_token)
        return await GitHubPagesService.detect(
            github_token=github_token,
            owner=request.owner,
            repository=request.repository,
            preferred_branch=current_user.deploy_branch,
        )
    except TokenDecryptionError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except GitHubPagesError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail or exc.message,
        ) from exc


@router.post(
    "/deploy",
    response_model=GitHubPagesDeployResponse,
    summary="Deploy repository to GitHub Pages",
)
async def deploy_to_github_pages(
    request: GitHubPagesDeployRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dispatch the Pages deployment workflow.

    SIDE EFFECT — Deployment row:
        A new PENDING row is written to the `deployments` table the
        moment GitHub Pages accepts the workflow dispatch. The row's
        `service_id` stores the workflow filename (e.g. `pages-html.yml`)
        so /refresh can post-filter the GitHub Actions runs API by
        workflow path. There is NO separate POST /deployments create
        endpoint — one user action = one atomic operation.
    """
    if not current_user.github_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Your GitHub access token is missing from our records. Please re-authenticate.")

    try:
        github_token = decrypt_secret(current_user.github_token)
        deploy_response = await GitHubPagesService.deploy(
            github_token=github_token,
            owner=request.owner,
            repository=request.repository,
            deployment_profile=request.deployment_profile,
            preferred_branch=current_user.deploy_branch,
        )
    except TokenDecryptionError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except GitHubPagesError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail or exc.message,
        ) from exc

    # Resolve the workflow filename (the .yml file in .github/workflows/)
    # from the resolved profile — the response carries only resolved_profile
    # + workflow_template, but we need the actual filename to track it on
    # the deployment row for /refresh to filter Actions runs by path.
    profile_definition = GitHubPagesService.PROFILE_DEFINITIONS.get(deploy_response.resolved_profile)
    workflow_filename = (
        profile_definition.workflow_filename
        if profile_definition
        else deploy_response.workflow_template
    )

    # Write the deployment row AFTER the workflow dispatch succeeds so a
    # dispatch failure doesn't leave an orphan row in our DB.
    await DeploymentService.create_from_pages_deploy(
        db,
        current_user.id,
        owner=request.owner,
        repo=request.repository,
        branch=deploy_response.branch,
        profile=deploy_response.resolved_profile,
        workflow_filename=workflow_filename,
    )

    return deploy_response


# ---------------------------------------------------------------------------
# Custom Domains  (Feature ① — Pages side; file-based via CNAME file)
# ---------------------------------------------------------------------------

@router.post(
    "/custom-domains/{owner}/{repository}",
    response_model=GitHubPagesCustomDomainResponse,
    summary="Attach a custom domain to a GitHub Pages site",
)
async def add_pages_custom_domain(
    owner: str,
    repository: str,
    payload: GitHubPagesCustomDomainRequest,
    current_user: User = Depends(get_current_user),
):
    """Commit a CNAME file (containing the domain) to the deploy branch.

    PAGES is FILE-BASED — the "claim" is literally a CNAME file at the
    repo root, committed via GitHub's Contents API (the SAME mechanism
    used to upload workflow YAMLs). GitHub Pages reads the file on the
    next build and starts serving the custom domain.

    Returns the DNS record the user must add at their registrar — a
    CNAME for subdomains, four A-records for apex (root) domains. The
    frontend renders a copy-paste card; clicking [I've added it → Verify]
    hits the /verify endpoint below.
    """
    github_token = _require_github_token(current_user)

    # Branch resolution order: explicit payload.branch → user's saved
    # deploy_branch → repo default_branch.
    branch = payload.branch or current_user.deploy_branch

    try:
        return await GitHubPagesService.add_custom_domain(
            github_token=github_token,
            owner=owner,
            repository=repository,
            domain=payload.domain,
            branch=branch,
        )
    except GitHubPagesError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail or exc.message,
        ) from exc


@router.post(
    "/custom-domains/{owner}/{repository}/{domain}/verify",
    response_model=GitHubPagesCustomDomainResponse,
    summary="Poll GitHub Pages for custom-domain DNS verification + HTTPS",
)
async def verify_pages_custom_domain(
    owner: str,
    repository: str,
    domain: str,
    current_user: User = Depends(get_current_user),
):
    """Re-read the Pages config to see if DNS has propagated + cert is ready.

    DNS propagation takes minutes to hours (rarely 48h). This endpoint
    NEVER blocks — it returns the current state so the UI can either
    confirm ("🔒 Live at https://...") or ask the user to re-check later.

    When the cert is available (`https: true` on the Pages config), we
    also try to enable HTTPS enforcement on the user's behalf.
    """
    github_token = _require_github_token(current_user)
    branch = current_user.deploy_branch

    try:
        return await GitHubPagesService.verify_custom_domain(
            github_token=github_token,
            owner=owner,
            repository=repository,
            domain=domain,
            branch=branch,
        )
    except GitHubPagesError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail or exc.message,
        ) from exc
