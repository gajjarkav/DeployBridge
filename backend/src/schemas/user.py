from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserProfileResponse(BaseModel):

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    username: str
    email: str | None = None
    avatar_url: str | None = None
    deploy_branch: str | None = None


class UserDeployBranchUpdate(BaseModel):
    deploy_branch: str | None = Field(default=None, max_length=255)
