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
