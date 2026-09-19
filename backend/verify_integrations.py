import asyncio
import httpx
from src.core.config import get_settings
from src.services.github import GitHubService

async def main():
    print("Verifying GitHub API connection...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.github.com/rate_limit")
            if response.status_code == 200:
                print("✅ GitHub API is reachable (Rate limit endpoint returned 200).")
            else:
                print(f"❌ GitHub API returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Failed to reach GitHub API: {e}")

    print("\nVerifying Render API connection...")
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.render.com/v1/services", headers={"Authorization": "Bearer fake_token"})
            if response.status_code in [200, 401]:
                # 401 means it's reachable but we don't have a valid token right now
                print(f"✅ Render API is reachable (Returned {response.status_code}, expected for fake/missing token).")
            else:
                print(f"❌ Render API returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Failed to reach Render API: {e}")


if __name__ == "__main__":
    asyncio.run(main())
