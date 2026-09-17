"""Pydantic schemas for the Render integration.

These mirror the shape of `schemas/github_pages.py` so the frontend can
reuse the same modal/form components. Two notable differences from the
GitHub Pages flow:

  1. Render has multiple runtime choices (python / node / docker), so
     `RenderRuntime` is an enum-like Literal, not a single static-site
     profile.
  2. Render deploys are asynchronous -- the create-service call returns
     immediately with a deployId, and the frontend polls
     /v1/render/services/{id} for build/live status. The deploy response
     therefore carries both the serviceId and the deployId so the
     frontend can start polling.
"""

from typing import Literal
from datetime import datetime

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Connection / disconnect / status
# ---------------------------------------------------------------------------

class RenderConnectRequest(BaseModel):
    """Body of POST /v1/render/connect.

    The key is the value the user copies from render.com → Account
    Settings → API Keys (typically `rnd_...`). We accept it as plain
    text over HTTPS, validate it once against GET /v1/owners, then
    store only the Fernet ciphertext.
    """
    api_key: str = Field(..., min_length=10, description="Render API key (rnd_...)")


class RenderConnectResponse(BaseModel):
    """Returned after a successful connect or refresh."""
    connected: bool = True
    owner_id: str = Field(..., description="Render workspace id (tea-...)")
    owner_name: str | None = Field(default=None, description="Workspace display name")
    owner_type: Literal["user", "team"] = Field(..., description="Personal vs team workspace")
    owner_email: str | None = None


class RenderStatusResponse(BaseModel):
    """Returned by GET /v1/render/status. NEVER includes the key."""
    connected: bool
    owner_id: str | None = None
    owner_name: str | None = None
    owner_type: Literal["user", "team"] | None = None
    owner_email: str | None = None


# ---------------------------------------------------------------------------
# Detect
# ---------------------------------------------------------------------------

RenderRuntime = Literal["python", "node", "docker"]
"""Render `serviceDetails.runtime` values we support for auto-detect.
Render also accepts `elixir | go | ruby | rust | image`, but those are
not part of the auto-detection rules in phase 1 -- the user can still
deploy them by passing the runtime explicitly in the deploy request.
"""

RenderPlan = Literal["free", "starter", "starter_plus", "standard", "standard_plus", "pro", "pro_plus"]
"""Subset of Render plan enum we expose in the UI. Render also accepts
CPU/memory specs like `0.5c-512mb`; we don't surface those in the
modal -- power users can edit the deploy request directly."""


class RenderDetectRequest(BaseModel):
    owner: str = Field(..., description="GitHub username or organization")
    repository: str = Field(..., description="GitHub repository name")


class RenderDetectResponse(BaseModel):
    """Result of auto-detecting a Render deployment profile from a repo.

    `runtime` is the only field the frontend strictly needs; the others
    are pre-filled suggestions the user can edit before clicking Deploy.
    """
    runtime: RenderRuntime
    build_command: str | None = None
    start_command: str | None = None
    dockerfile_path: str | None = Field(default=None, description="Set only when runtime=docker")
    plan: RenderPlan = "free"
    branch: str
    reason: str
    env_var_suggestions: dict[str, str] = Field(
        default_factory=dict,
        description="Best-effort env var suggestions (e.g. PORT, NODE_ENV)",
    )


# ---------------------------------------------------------------------------
# Deploy
# ---------------------------------------------------------------------------

class RenderEnvVar(BaseModel):
    """Single env var sent to Render on create-service.

    Render accepts either `value` (plaintext, stored encrypted on
    Render's side) or `generateValue: true` (Render generates a strong
    random value, used for secrets the user doesn't want to type).
    """
    key: str = Field(..., min_length=1, max_length=256)
    value: str = Field(default="")
    generate_value: bool = Field(default=False, description="If true, Render generates a random value")


class RenderDeployRequest(BaseModel):
    """Body of POST /v1/render/deploy.

    All `*_command` fields are optional -- if the caller passes
    `runtime: "docker"`, the Dockerfile is read from the repo root and
    `dockerfile_path` defaults to `./Dockerfile`. For native runtimes
    Render requires both build and start commands; we pre-fill them
    from /detect so the user only has to confirm.
    """
    owner: str = Field(..., description="GitHub owner (used for repo URL)")
    repository: str = Field(..., description="GitHub repository name")
    branch: str = Field(..., description="Branch to deploy from")
    service_name: str = Field(..., min_length=2, max_length=63,
                              description="Becomes https://<name>.onrender.com")
    runtime: RenderRuntime
    build_command: str | None = None
    start_command: str | None = None
    dockerfile_path: str | None = Field(default="./Dockerfile")
    plan: RenderPlan = "free"
    auto_deploy: bool = Field(default=True)
    env_vars: list[RenderEnvVar] = Field(default_factory=list)


class RenderDeployResponse(BaseModel):
    """Returned by POST /v1/render/deploy.

    Render create-service returns `{service, deployId}`. We pass both
    through plus the public URL Render assigns immediately (the URL
    exists from t=0 even before the build finishes; it returns 502
    until the deploy goes live).
    """
    success: bool
    service_id: str
    deploy_id: str
    service_url: str | None = None
    dashboard_url: str | None = None
    message: str


# ---------------------------------------------------------------------------
# Service list / detail / redeploy
# ---------------------------------------------------------------------------

class RenderServiceSummary(BaseModel):
    """Compact service shape for the Deployments table.

    Mirrors only the fields the frontend needs to render a row; the
    raw Render `service` object has 30+ fields and we don't want to leak
    internals like IP allow lists to the browser.
    """
    service_id: str
    name: str
    url: str | None = None
    dashboard_url: str | None = None
    runtime: str | None = None
    plan: str | None = None
    status: str | None = Field(default=None, description="suspended|not_suspended")
    repo: str | None = None
    branch: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    latest_deploy_status: str | None = Field(
        default=None,
        description="Polled from /v1/services/{id}/deploys[0].status",
    )


class RenderServiceDetail(RenderServiceSummary):
    """Adds latest deploy info for the service detail page."""
    latest_deploy_id: str | None = None
    latest_deploy_commit: str | None = None
    latest_deploy_trigger: str | None = None
    latest_deploy_started_at: datetime | None = None
    latest_deploy_finished_at: datetime | None = None


class RenderRedeployResponse(BaseModel):
    success: bool
    deploy_id: str
    message: str


# ---------------------------------------------------------------------------
# Custom domains
# ---------------------------------------------------------------------------

class RenderCustomDomainRequest(BaseModel):
    domain: str = Field(..., description="The custom hostname to attach, e.g. app.example.com")


class RenderCustomDomainResponse(BaseModel):
    """Response from adding a custom domain.

    Render's API does NOT return DNS records -- only verificationStatus.
    We derive the CNAME target from the service's `onrender.com` URL
    server-side (since we already know it) and return both the
    verificationStatus and the suggested CNAME so the frontend can show
    the user exactly what to add at their DNS provider.
    """
    domain_id: str
    name: str
    domain_type: str | None = None
    verification_status: str
    cname_target: str | None = None
    message: str
