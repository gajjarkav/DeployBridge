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
    detected_profile: ResolvedDeploymentProfile
    supported_profiles: list[DeploymentProfile]
    reason: str
    branch: str


class GitHubPagesDeployResponse(BaseModel):
    success: bool
    message: str
    resolved_profile: ResolvedDeploymentProfile
    workflow_template: str
    branch: str
