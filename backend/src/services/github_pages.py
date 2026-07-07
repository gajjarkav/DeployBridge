import asyncio
import httpx
import base64
from pathlib import Path

from ..schemas.github_pages import GitHubPagesDeployResponse
from ..core.exception import (
    RepositoryNotFoundError,
    GitHubAPIError,
)


class GitHubPagesService:

    GITHUB_API_BASE_URL = "https://api.github.com"
    REQUIRED_OAUTH_SCOPES = {"workflow"}
    TEMPLATE_DIRECTORY = (
        Path(__file__).resolve().parent.parent
        / "templates"
        / "github_pages"
    )

    @classmethod
    async def deploy(
        cls,
        github_token: str,
        owner: str,
        repository: str,
    ) -> GitHubPagesDeployResponse:
        """Initialize a GitHub pages deployment"""

        print(f"\n🚀 Starting GitHub Pages deployment for {owner}/{repository}")

        repository_data = await cls._verify_repository(
            github_token=github_token,
            owner=owner,
            repository=repository,
        )

        default_branch = repository_data.get("default_branch")
        if not default_branch:
            raise GitHubAPIError(
                message="Repository has no default branch",
                detail="This repository appears to be empty. Add your HTML, CSS, and JavaScript files first, then try again.",
                status_code=400,
            )

        await cls._validate_static_site_repository(
            github_token=github_token,
            owner=owner,
            repository=repository,
            default_branch=default_branch,
        )

        await cls._upsert_workflow(
            github_token=github_token,
            owner=owner,
            repository=repository,
            default_branch=default_branch,
        )

        await cls._configure_pages(
            github_token=github_token,
            owner=owner,
            repository=repository,
            default_branch=default_branch,
        )

        await cls._dispatch_workflow(
            github_token=github_token,
            owner=owner,
            repository=repository,
            default_branch=default_branch,
        )

        print(f"✓ GitHub Pages deployment completed successfully!\n")

        return GitHubPagesDeployResponse(
            success=True,
            message=f'GitHub Pages deployment started for "{repository}". GitHub Actions is now running on the "{default_branch}" branch.',
        )


    @classmethod
    async def _verify_repository(
        cls,
        github_token: str,
        owner: str,
        repository: str,
    ) -> dict:
        """verify that the repository exists and the authenticated user has access to it"""

        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json"
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{cls.GITHUB_API_BASE_URL}/repos/{owner}/{repository}",
                headers=headers,
            )

        if response.status_code == 200:
            cls._ensure_required_scopes(response.headers.get("X-OAuth-Scopes", ""))
            print(f"✓ Repository verified: {owner}/{repository}")
            return response.json()

        if response.status_code == 404:
            raise RepositoryNotFoundError(
                message="Repository not found",
                detail="The repository does not exist or you do not have permission to access it",
            )

        if response.status_code == 401:
            raise GitHubAPIError(
                message="Authentication failed",
                detail="GitHub token is invalid or expired. Please re-authenticate.",
                status_code=401,
            )

        if response.status_code == 403:
            raise GitHubAPIError(
                message="Repository access denied",
                detail="GitHub rejected this request. Make sure your account can manage this repository and GitHub Pages is allowed for it.",
                status_code=403,
            )

        raise GitHubAPIError(
            message="GitHub API request failed",
            detail=f"GitHub returned status code {response.status_code}: {response.text}",
            status_code=400,
        )

    @classmethod
    def _read_template(
        cls,
        template_name: str,
    ) -> str:
        """Read a GitHub Actions workflow template"""

        template_path = cls.TEMPLATE_DIRECTORY / template_name

        return template_path.read_text(
            encoding="utf-8",
        )

    @classmethod
    def _ensure_required_scopes(cls, raw_scopes: str) -> None:
        scopes = {
            scope.strip()
            for scope in raw_scopes.split(",")
            if scope.strip()
        }

        missing_scopes = sorted(cls.REQUIRED_OAUTH_SCOPES - scopes)
        if not missing_scopes:
            return

        missing_scope_list = ", ".join(missing_scopes)
        raise GitHubAPIError(
            message="Missing GitHub OAuth scopes",
            detail=(
                "Your current GitHub login is missing the required scope(s): "
                f"{missing_scope_list}. Please log out, sign in with GitHub again, and approve the updated permissions."
            ),
            status_code=403,
        )

    @classmethod
    async def _validate_static_site_repository(
        cls,
        github_token: str,
        owner: str,
        repository: str,
        default_branch: str,
    ) -> None:
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
        }

        url = f"{cls.GITHUB_API_BASE_URL}/repos/{owner}/{repository}/contents"
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                headers=headers,
                params={"ref": default_branch},
            )

        if response.status_code != 200:
            raise GitHubAPIError(
                message="Unable to inspect repository files",
                detail="DeployBridge could not verify whether this repository is a plain HTML/CSS/JS site.",
                status_code=400,
            )

        root_items = response.json()
        if not isinstance(root_items, list):
            return

        root_names = {
            item.get("name", "").lower()
            for item in root_items
        }
        unsupported_markers = {
            "package.json",
            "package-lock.json",
            "yarn.lock",
            "pnpm-lock.yaml",
            "vite.config.js",
            "vite.config.ts",
            "next.config.js",
            "next.config.mjs",
            "nuxt.config.ts",
            "angular.json",
        }
        found_markers = sorted(root_names & unsupported_markers)

        if found_markers:
            raise GitHubAPIError(
                message="Unsupported repository type",
                detail=(
                    "This deployment flow currently supports only plain HTML, CSS, and JavaScript repositories. "
                    f"Found framework/build markers: {', '.join(found_markers)}."
                ),
                status_code=400,
            )

    @classmethod
    async def _upsert_workflow(
        cls,
        github_token: str,
        owner: str,
        repository: str,
        default_branch: str,
    ) -> None:
        """create or update the github actions workflow file inside the user's repo"""

        workflow = cls._read_template("html.yml").replace(
            "__DEFAULT_BRANCH__",
            default_branch,
        )

        encoded_workflow = base64.b64encode(
            workflow.encode("utf-8")
        ).decode("utf-8")

        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json"
        }

        # Now create the workflow file
        url = f"{cls.GITHUB_API_BASE_URL}/repos/{owner}/{repository}/contents/.github/workflows/html.yml"

        # Check if workflow file already exists to get its SHA
        sha = None
        async with httpx.AsyncClient() as client:
            get_response = await client.get(url, headers=headers)
            if get_response.status_code == 200:
                sha = get_response.json().get("sha")
                print(f"  Workflow file exists, SHA: {sha[:8]}...")

        payload = {
            "message": "DeployBridge: Add GitHub Pages Workflow",
            "content": encoded_workflow,
            "branch": default_branch,
        }
        
        # Add SHA if file exists (required for updates)
        if sha:
            payload["sha"] = sha

        print(f"  Creating/updating workflow file...")
        
        async with httpx.AsyncClient() as client:
            response = await client.put(
                url,
                headers=headers,
                json=payload,
            )

        if response.status_code not in (200, 201):
            print(f"✗ Workflow creation failed")
            print(f"  Status: {response.status_code}")
            print(f"  Response: {response.text}")
            raise GitHubAPIError(
                message="Failed to create workflow",
                detail=(
                    "GitHub could not create the Pages workflow file. "
                    "If you logged in before the new permissions were added, log out and sign in with GitHub again."
                    f" GitHub response: {response.text}"
                ),
                status_code=400,
            )
        
        print(f"✓ Workflow created/updated successfully")

    @classmethod
    async def _configure_pages(
        cls,
        github_token: str,
        owner: str,
        repository: str,
        default_branch: str,
    ) -> None:
        """Create or update GitHub Pages to use GitHub Actions."""

        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
        }

        payload = {
            "build_type": "workflow",
            "source": {
                "branch": default_branch,
                "path": "/",
            },
        }

        async with httpx.AsyncClient() as client:
            pages_url = f"{cls.GITHUB_API_BASE_URL}/repos/{owner}/{repository}/pages"
            pages_response = await client.get(
                pages_url,
                headers=headers,
            )

            if pages_response.status_code == 404:
                print("  Creating GitHub Pages site...")
                response = await client.post(
                    pages_url,
                    headers=headers,
                    json=payload,
                )
            elif pages_response.status_code == 200:
                print("  Updating existing GitHub Pages site...")
                response = await client.put(
                    pages_url,
                    headers=headers,
                    json=payload,
                )
            else:
                response = pages_response

        if response.status_code in (201, 204):
            print(f"✓ GitHub Pages configured successfully (status: {response.status_code})")
            return

        print("✗ Failed to configure GitHub Pages")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text}")

        raise GitHubAPIError(
            message="Failed to configure GitHub Pages",
            detail=response.text,
            status_code=400,
        )

    @classmethod
    async def _dispatch_workflow(
        cls,
        github_token: str,
        owner: str,
        repository: str,
        default_branch: str,
    ) -> None:
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
        }

        payload = {
            "ref": default_branch,
        }

        url = (
            f"{cls.GITHUB_API_BASE_URL}/repos/{owner}/{repository}"
            "/actions/workflows/html.yml/dispatches"
        )

        print(f'  Triggering workflow_dispatch on "{default_branch}"...')

        response = None
        async with httpx.AsyncClient() as client:
            for attempt in range(1, 4):
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload,
                )

                if response.status_code == 204:
                    print("✓ Workflow run triggered successfully")
                    return

                if response.status_code not in (404, 422) or attempt == 3:
                    break

                print(f"  Workflow not ready yet (attempt {attempt}/3). Retrying...")
                await asyncio.sleep(1)

        print("✗ Failed to trigger workflow run")
        print(f"  Status: {response.status_code}")
        print(f"  Response: {response.text}")

        raise GitHubAPIError(
            message="Failed to start the GitHub Actions workflow",
            detail=response.text,
            status_code=400,
        )

    @classmethod
    async def _request(
        cls,
        method: str,
        url: str,
        github_token: str,
        **kwargs,
    ) -> httpx.Response:

        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
        }

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                **kwargs,
            )

        return response
