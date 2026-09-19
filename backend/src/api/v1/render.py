"""Render integration endpoints.

Mirrors the shape of `api/v1/github_pages.py` so the frontend can
reuse the same modal/flow conventions:

  - /connect   POST   save+validate the per-user Render API key
  - /connect   DELETE disconnect (null columns)
  - /status    GET    "am I connected?" -- never returns the key
  - /detect    POST   detect Render profile (runtime/build/start) from a repo
  - /deploy    POST   create service + trigger deploy
  - /services  GET    list user's Render services
  - /services/{id} GET    service + latest deploy status
  - /services/{id}/redeploy POST   trigger a manual redeploy
  - /services/{id}/custom-domain POST   add a custom domain
  - /services/{id}/custom-domain/{name}/verify POST   poll DNS verification

Auth: every endpoint requires a valid session JWT (via
get_current_user). The Render API key is decrypted on-demand from
the user row; we never expose the plaintext key in responses.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.crypto import TokenDecryptionError, decrypt_secret, encrypt_secret
from ...core.exception import RenderError
from ...db.session import get_db
from ...models.user import User
from ...schemas.render import (
    RenderConnectRequest,
    RenderConnectResponse,
    RenderCustomDomainRequest,
    RenderCustomDomainResponse,
    RenderDeployRequest,
    RenderDeployResponse,
    RenderDetectRequest,
    RenderDetectResponse,
    RenderRedeployResponse,
    RenderServiceDetail,
    RenderServiceSummary,
    RenderStatusResponse,
)
from ...services.deployment_service import DeploymentService
from ...services.render import RenderService
from ..dependencies import get_current_user


router = APIRouter()


def _require_render_key(current_user: User) -> str:
    """Common guard: the user must have a connected Render API key.

    Mirrors the github_pages.py guard for `github_token`. Returns the
    decrypted plaintext key for use in this request only; the
    ciphertext stays in the DB.
    """
    if not current_user.render_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Render integration is not connected. Visit Settings → Integrations "
                   "→ Connect Render to paste your API key.",
        )
    try:
        return decrypt_secret(current_user.render_api_key)
    except TokenDecryptionError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc


# ---------------------------------------------------------------------------
# Connect / disconnect / status
# ---------------------------------------------------------------------------

@router.post(
    "/connect",
    response_model=RenderConnectResponse,
    summary="Save and validate a Render API key",
)
async def connect_render(
    payload: RenderConnectRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Validate the API key against GET /v1/owners, then store encrypted.

    On success we cache the personal workspace id (tea-...) on the user
    row so subsequent deploy/list calls don't have to re-resolve it.
    """
    try:
        owner = await RenderService.validate_key_and_resolve_owner(payload.api_key)
    except RenderError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail or exc.message,
        ) from exc

    current_user.render_api_key = encrypt_secret(payload.api_key)
    current_user.render_owner_id = owner["id"]
    await db.commit()
    await db.refresh(current_user)

    return RenderService.build_connect_response(owner)


@router.delete(
    "/connect",
    response_model=RenderStatusResponse,
    summary="Disconnect Render integration",
)
async def disconnect_render(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Null out both render_api_key and render_owner_id.

    Does NOT delete any Render-side services -- those keep running on
    Render. The user can re-connect at any time to regain control.
    """
    current_user.render_api_key = None
    current_user.render_owner_id = None
    await db.commit()
    await db.refresh(current_user)

    return RenderStatusResponse(connected=False)


@router.get(
    "/status",
    response_model=RenderStatusResponse,
    summary="Check if Render integration is connected",
)
async def render_status(
    current_user: User = Depends(get_current_user),
):
    """Returns connected=True + cached owner info if the user has a key.

    NEVER returns the key itself. For a live validity check (has the
    key been revoked?), the frontend can call /v1/render/services which
    will 401 if the key is invalid.
    """
    if not current_user.render_api_key:
        return RenderStatusResponse(connected=False)
    return RenderStatusResponse(
        connected=True,
        owner_id=current_user.render_owner_id,
    )


# ---------------------------------------------------------------------------
# Detect
# ---------------------------------------------------------------------------

@router.post(
    "/detect",
    response_model=RenderDetectResponse,
    summary="Detect Render runtime profile from a GitHub repo",
)
async def detect_render_profile(
    request: RenderDetectRequest,
    current_user: User = Depends(get_current_user),
):
    """Inspect the repo via the user's GitHub token and recommend a runtime.

    Reuses GitHubPagesService.build_repository_context so the SAME repo
    inspection code powers both Pages and Render detect -- no drift
    between the two platforms.
    """
    if not current_user.github_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your GitHub access token is missing. Please re-authenticate.",
        )

    try:
        github_token = decrypt_secret(current_user.github_token)
    except TokenDecryptionError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    try:
        return await RenderService.detect(
            github_token=github_token,
            owner=request.owner,
            repository=request.repository,
            preferred_branch=current_user.deploy_branch,
        )
    except RenderError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail or exc.message,
        ) from exc


# ---------------------------------------------------------------------------
# Deploy
# ---------------------------------------------------------------------------

@router.post(
    "/deploy",
    response_model=RenderDeployResponse,
    summary="Create a Render web service and trigger a deploy",
)
async def deploy_to_render(
    request: RenderDeployRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create the service on Render with env vars + auto-deploy on.

    Returns the new serviceId and deployId immediately; the frontend
    polls /v1/render/services/{serviceId} for build/live status.
    
    SIDE EFFECT — Deployment row:
        A new BUILDING row is written to the `deployments` table the
        moment Render confirms the create-service call. There is NO
        separate POST /deployments create endpoint; one user action =
        one atomic operation. The frontend's Deployments page reads
        these rows instead of localStorage.
    """
    api_key = _require_render_key(current_user)
    owner_id = current_user.render_owner_id
    if not owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Render owner id is missing. Re-connect in Settings to refresh it.",
        )

    try:
        deploy_response = await RenderService.create_web_service(
            api_key=api_key,
            owner_id=owner_id,
            request=request,
        )
    except RenderError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail or exc.message,
        ) from exc

    # Write the deployment row. We do this AFTER the Render call returns
    # so a Render-side failure doesn't leave an orphan row in our DB.
    await DeploymentService.create_from_render_deploy(
        db,
        current_user.id,
        owner=request.owner,
        repo=request.repository,
        branch=request.branch,
        runtime=request.runtime,
        service_id=deploy_response.service_id,
        deploy_id=deploy_response.deploy_id,
        service_url=deploy_response.service_url,
    )
    # db.commit() happens in get_db() on successful exit; if anything
    # below raises, the row write rolls back too — atomic.

    return deploy_response

    


# ---------------------------------------------------------------------------
# Service list / detail / redeploy / custom domains
# ---------------------------------------------------------------------------

@router.get(
    "/services",
    response_model=list[RenderServiceSummary],
    summary="List user's Render services",
)
async def list_render_services(
    current_user: User = Depends(get_current_user),
):
    api_key = _require_render_key(current_user)
    try:
        return await RenderService.list_services(
            api_key=api_key,
            owner_id=current_user.render_owner_id,
            limit=50,
        )
    except RenderError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail or exc.message,
        ) from exc


@router.get(
    "/services/{service_id}",
    response_model=RenderServiceDetail,
    summary="Get a Render service with its latest deploy status",
)
async def get_render_service(
    service_id: str,
    current_user: User = Depends(get_current_user),
):
    api_key = _require_render_key(current_user)
    try:
        return await RenderService.get_service(api_key=api_key, service_id=service_id)
    except RenderError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail or exc.message,
        ) from exc


@router.post(
    "/services/{service_id}/redeploy",
    response_model=RenderRedeployResponse,
    summary="Trigger a manual redeploy on Render",
)
async def redeploy_render_service(
    service_id: str,
    current_user: User = Depends(get_current_user),
):
    api_key = _require_render_key(current_user)
    try:
        deploy_id = await RenderService.trigger_deploy(
            api_key=api_key,
            service_id=service_id,
            clear_cache=False,
        )
        return RenderRedeployResponse(
            success=True,
            deploy_id=deploy_id,
            message=f"Redeploy triggered (deploy id {deploy_id}).",
        )
    except RenderError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail or exc.message,
        ) from exc


@router.post(
    "/services/{service_id}/custom-domain",
    response_model=RenderCustomDomainResponse,
    summary="Attach a custom domain to a Render service",
)
async def add_custom_domain(
    service_id: str,
    payload: RenderCustomDomainRequest,
    current_user: User = Depends(get_current_user),
):
    """Add a custom hostname. Returns the CNAME target the user must
    add at their DNS provider -- Render's API does NOT return DNS
    records, so we derive the CNAME target from the service's
    `onrender.com` URL server-side.
    """
    api_key = _require_render_key(current_user)
    try:
        return await RenderService.add_custom_domain(
            api_key=api_key,
            service_id=service_id,
            domain=payload.domain,
        )
    except RenderError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail or exc.message,
        ) from exc


@router.post(
    "/services/{service_id}/custom-domain/{domain_name_or_id}/verify",
    response_model=RenderCustomDomainResponse,
    summary="Poll Render for custom-domain DNS verification",
)
async def verify_custom_domain(
    service_id: str,
    domain_name_or_id: str,
    current_user: User = Depends(get_current_user),
):
    api_key = _require_render_key(current_user)
    try:
        return await RenderService.verify_custom_domain(
            api_key=api_key,
            service_id=service_id,
            domain_name_or_id=domain_name_or_id,
        )
    except RenderError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail or exc.message,
        ) from exc