import httpx
from fastapi import HTTPException, status

from src.core.config import get_settings


settings = get_settings()

class GitHubService:

    TOKEN_URL = "https://github.com/login/oauth/access_token"
    USER_API_URL = "https://api.github.com/user"
    EMAILS_API_URL = "https://api.github.com/user/emails"
        

    @classmethod
    async def get_access_token(cls, code: str) -> str:
        """
        exchanges the temporary code from GitHub for  an access token.
        """
        headers = {
            "Accept": "application/json"
        }
        data = {
            "client_id": settings.GITHUB_CLIENT_ID,
            "client_secret": settings.GITHUB_CLIENT_SECRET,
            "code": code,
        }

        async with httpx.AsyncClient() as client:
            response = await  client.post(cls.TOKEN_URL, data=data, headers=headers)
            response_data = response.json()

            if "error" in response_data:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"github OAuth error: {response_data.get('error_description', "Unknown error")}"                    
                )

            return {
                "access_token": response_data["access_token"],
                "token_type": response_data.get("token_type"),
                "scope": response_data.get("scope"),
            }

    
    @classmethod
    async def get_user_profile(cls, access_token: str) -> dict:
        """
        fetches the user's profile and primary email using the access token.
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github.v3+json",
        }

        async with httpx.AsyncClient() as client:
            profile_response = await client.get(cls.USER_API_URL, headers=headers)
            if profile_response.status_code != 200:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Failed to fetch Github profile!🔴")
            
            profile_data = profile_response.json()

            emails_response = await client.get(cls.EMAILS_API_URL, headers=headers)
            primary_email = None

            if emails_response.status_code == 200:
                emails = emails_response.json()

                for emails_obj in emails:
                    if emails_obj.get("primary") and emails_obj.get("verified"):
                        primary_email = emails_obj.get("email")
                        break

            return {
                "github_id": str(profile_data["id"]),
                "username": profile_data["login"],
                "email": primary_email,
                "avatar_url": profile_data.get("avatar_url"),
            }