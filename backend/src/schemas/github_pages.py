from pydantic import BaseModel, Field

class GitHubPagesDeployRequest(BaseModel):
    owner: str = Field(..., description="GitHub username or organization")
    repository: str = Field(..., description="Repository name")


class GitHubPagesDeployResponse(BaseModel):
    success: bool
    message: str