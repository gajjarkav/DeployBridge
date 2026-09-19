from typing import Literal

from pydantic import BaseModel, Field


DeploymentProfile = Literal["auto", "html", "jekyll", "node-static", "next-static"]
ResolvedDeploymentProfile = Literal["html", "jekyll", "node-static", "next-static"]


class GitHubPagesRepositoryRequest(BaseModel):
    owner: str = Field(..., description="GitHub username or organization")
    repository: str = Field(..., description="Repository name")


class GitHubPagesDeployRequest(GitHubPagesRepositoryRequest):
    deployment_profile: DeploymentProfile = Field(
        default="auto",
        description="Requested deployment profile or auto-detect",
    )


class GitHubPagesDetectResponse(BaseModel):
    """Response shape for POST /v1/github-pages/detect.

    When `detected_profile` is None and `recommended_platform` is set,
    the repo is NOT a GitHub Pages candidate -- the frontend should
    show a "This looks like a server app → Deploy to Render" CTA and
    route the user to the Render detect/deploy flow. When
    `detected_profile` is set, GitHub Pages is the right target.
    """
    detected_profile: ResolvedDeploymentProfile | None = None
    supported_profiles: list[DeploymentProfile] = Field(default_factory=list)
    reason: str
    branch: str
    recommended_platform: Literal["render", None] = Field(
        default=None,
        description="Set to 'render' when the repo is a server app that Pages cannot host.",
    )


class GitHubPagesDeployResponse(BaseModel):
    success: bool
    message: str
    resolved_profile: ResolvedDeploymentProfile
    workflow_template: str
    branch: str


# ---------------------------------------------------------------------------
# Custom domains (Feature ① — file-based: a CNAME file in the deploy branch)
# ---------------------------------------------------------------------------

GitHubPagesCustomDomainStatus = Literal[
    "waiting_for_dns",   # CNAME file just committed; GitHub hasn't verified yet
    "verified",          # DNS resolves; cert is being issued
    "live",              # HTTPS cert issued; https://<domain> serves the site
]


class GitHubPagesCustomDomainRequest(BaseModel):
    """Body of POST /v1/github-pages/{owner}/{repo}/custom-domain.

    Pages is FILE-BASED: the "claim" is literally a CNAME file containing
    the domain, committed to the deploy branch via GitHub's Contents API
    — the SAME mechanism used to upload workflow YAMLs. GitHub then
    verifies DNS and offers an "Enforce HTTPS" toggle (auto-issued by
    Let's Encrypt). The UX is identical to Render's; the mechanism is
    completely different. THAT is DeployBridge's whole value prop.
    """
    domain: str = Field(..., description="The custom hostname to attach, e.g. notes.kumar.dev")
    branch: str | None = Field(
        default=None,
        description="Branch to commit the CNAME file to. Defaults to the "
                    "user's saved deploy_branch or the repo's default branch.",
    )


class GitHubPagesCustomDomainResponse(BaseModel):
    """Returned by both add + verify Pages custom-domain endpoints."""
    domain: str
    branch: str
    cname_target: str = Field(
        ...,
        description="What the user's DNS provider's CNAME record should point to. "
                    "For Pages subdomains this is <user>.github.io; for apex "
                    "domains it's the four 185.199.108-111.153 A-records.",
    )
    record_type: Literal["CNAME", "A"] = Field(
        ...,
        description="DNS record type the user must add at their registrar.",
    )
    record_name: str = Field(
        ...,
        description="DNS record name (the subdomain part, or '@' for apex).",
    )
    https_enabled: bool = Field(
        default=False,
        description="True once GitHub has issued the Let's Encrypt cert. The "
                    "Pages config endpoint exposes `https_enforced`; we enable "
                    "it on verify() when the cert is available.",
    )
    status: GitHubPagesCustomDomainStatus
    message: str
