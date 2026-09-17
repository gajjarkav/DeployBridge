from email.policy import default
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
    render_connected: bool = Field(
        default=False,
        description="True when the user has a Render API key stored (encrypted). "
                    "The plaintext key is never returned; this is just a UI hint.",
    )


class UserDeployBranchUpdate(BaseModel):
    deploy_branch: str | None = Field(default=None, max_length=255)
