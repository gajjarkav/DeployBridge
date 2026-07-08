import asyncio
import base64
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from ..core.exception import GitHubAPIError, RepositoryNotFoundError
from ..schemas.github_pages import (
    DeploymentProfile,
    GitHubPagesDeployResponse,
    GitHubPagesDetectResponse,
    ResolvedDeploymentProfile,
)


@dataclass(frozen=True)
class DeploymentProfileDefinition:
    key: ResolvedDeploymentProfile
    workflow_template: str
    workflow_filename: str


@dataclass
class RepositoryContext:
    owner: str
    repository: str
    default_branch: str
    root_items: list[dict[str, Any]]
    root_names: set[str]
    root_directories: set[str]
    package_json: dict[str, Any] | None
    package_name: str | None
    dependencies: set[str]
    dev_dependencies: set[str]
    scripts: dict[str, str]
    next_config_text: str | None
    gemfile_text: str | None


class GitHubPagesService:
    GITHUB_API_BASE_URL = "https://api.github.com"
    REQUIRED_OAUTH_SCOPES = {"workflow"}
    SUPPORTED_PROFILES: list[DeploymentProfile] = [
        "auto",
        "html",
        "jekyll",
        "node-static",
        "next-static",
    ]
    PROFILE_DEFINITIONS: dict[ResolvedDeploymentProfile, DeploymentProfileDefinition] = {
        "html": DeploymentProfileDefinition(
            key="html",
            workflow_template="html.yml",
            workflow_filename="html.yml",
        ),
        "jekyll": DeploymentProfileDefinition(
            key="jekyll",
            workflow_template="jekyll.yml",
            workflow_filename="jekyll.yml",
        ),
        "node-static": DeploymentProfileDefinition(
            key="node-static",
            workflow_template="node-static.yml",
            workflow_filename="node-static.yml",
        ),
        "next-static": DeploymentProfileDefinition(
            key="next-static",
            workflow_template="next-static.yml",
            workflow_filename="next-static.yml",
        ),
    }
    NODE_STATIC_DEPENDENCY_MARKERS = {
        "react",
        "react-dom",
        "react-scripts",
        "vite",
        "vue",
        "@vue/cli-service",
        "svelte",
        "@sveltejs/vite-plugin-svelte",
        "astro",
        "gatsby",
        "@angular/core",
        "@angular/cli",
        "nuxt",
        "@11ty/eleventy",
        "preact",
    }
    SERVER_RUNTIME_MARKERS = {
        "express",
        "fastify",
        "koa",
        "@nestjs/core",
        "hono",
        "next-auth",
        "socket.io",
        "@remix-run/node",
        "@remix-run/react",
    }
    NEXT_CONFIG_CANDIDATES = (
        "next.config.js",
        "next.config.mjs",
        "next.config.ts",
    )
    TEMPLATE_DIRECTORY = (
        Path(__file__).resolve().parent.parent / "templates" / "github_pages"
    )

    @classmethod
    async def detect(
        cls,
        github_token: str,
        owner: str,
        repository: str,
    ) -> GitHubPagesDetectResponse:
        repository_data = await cls._verify_repository(
            github_token=github_token,
            owner=owner,
            repository=repository,
        )
        context = await cls._build_repository_context(
            github_token=github_token,
            owner=owner,
            repository=repository,
            repository_data=repository_data,
        )
        detected_profile, reason = cls._detect_profile(context)

        return GitHubPagesDetectResponse(
            detected_profile=detected_profile,
            supported_profiles=cls.SUPPORTED_PROFILES,
            reason=reason,
        )

    @classmethod
    async def deploy(
        cls,
        github_token: str,
        owner: str,
        repository: str,
        deployment_profile: DeploymentProfile = "auto",
    ) -> GitHubPagesDeployResponse:
        print(f"\n🚀 Starting GitHub Pages deployment for {owner}/{repository}")

        repository_data = await cls._verify_repository(
            github_token=github_token,
            owner=owner,
            repository=repository,
        )
        context = await cls._build_repository_context(
            github_token=github_token,
            owner=owner,
            repository=repository,
            repository_data=repository_data,
        )

        resolved_profile, reason = cls._resolve_requested_profile(
            context=context,
            requested_profile=deployment_profile,
        )
        profile_definition = cls.PROFILE_DEFINITIONS[resolved_profile]

        print(f"✓ Resolved deployment profile: {resolved_profile} ({reason})")

        await cls._remove_other_workflows(
            github_token=github_token,
            owner=owner,
            repository=repository,
            default_branch=context.default_branch,
            keep_filename=profile_definition.workflow_filename,
        )
        await cls._upsert_workflow(
            github_token=github_token,
            owner=owner,
            repository=repository,
            default_branch=context.default_branch,
            profile_definition=profile_definition,
        )
        await cls._configure_pages(
            github_token=github_token,
            owner=owner,
            repository=repository,
            default_branch=context.default_branch,
        )
        await cls._dispatch_workflow(
            github_token=github_token,
            owner=owner,
            repository=repository,
            default_branch=context.default_branch,
            workflow_filename=profile_definition.workflow_filename,
        )

        print("✓ GitHub Pages deployment completed successfully!\n")

        return GitHubPagesDeployResponse(
            success=True,
            message=(
                f'GitHub Pages deployment started for "{repository}" using the '
                f'"{resolved_profile}" profile on "{context.default_branch}".'
            ),
            resolved_profile=resolved_profile,
            workflow_template=profile_definition.workflow_template,
        )

    @classmethod
    async def _verify_repository(
        cls,
        github_token: str,
        owner: str,
        repository: str,
    ) -> dict[str, Any]:
        headers = cls._build_headers(github_token)

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
                detail="The repository does not exist or you do not have permission to access it.",
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
    async def _build_repository_context(
        cls,
        github_token: str,
        owner: str,
        repository: str,
        repository_data: dict[str, Any],
    ) -> RepositoryContext:
        default_branch = repository_data.get("default_branch")
        if not default_branch:
            raise GitHubAPIError(
                message="Repository has no default branch",
                detail="This repository appears to be empty. Add your site files first, then try again.",
                status_code=400,
            )

        root_items = await cls._get_repository_contents(
            github_token=github_token,
            owner=owner,
            repository=repository,
            path="",
            ref=default_branch,
        )
        root_names = {
            item.get("name", "").lower()
            for item in root_items
            if item.get("name")
        }
        root_directories = {
            item.get("name", "").lower()
            for item in root_items
            if item.get("type") == "dir" and item.get("name")
        }

        package_json = await cls._get_json_file(
            github_token=github_token,
            owner=owner,
            repository=repository,
            path="package.json",
            ref=default_branch,
        )
        next_config_text = await cls._read_first_available_file(
            github_token=github_token,
            owner=owner,
            repository=repository,
            ref=default_branch,
            candidates=cls.NEXT_CONFIG_CANDIDATES,
        )
        gemfile_text = await cls._get_text_file(
            github_token=github_token,
            owner=owner,
            repository=repository,
            path="Gemfile",
            ref=default_branch,
        )

        scripts = {}
        dependencies: set[str] = set()
        dev_dependencies: set[str] = set()
        package_name = None

        if package_json:
            package_name = package_json.get("name")
            scripts = {
                key: value
                for key, value in package_json.get("scripts", {}).items()
                if isinstance(value, str)
            }
            dependencies = set(package_json.get("dependencies", {}).keys())
            dev_dependencies = set(package_json.get("devDependencies", {}).keys())

        return RepositoryContext(
            owner=owner,
            repository=repository,
            default_branch=default_branch,
            root_items=root_items,
            root_names=root_names,
            root_directories=root_directories,
            package_json=package_json,
            package_name=package_name,
            dependencies=dependencies,
            dev_dependencies=dev_dependencies,
            scripts=scripts,
            next_config_text=next_config_text,
            gemfile_text=gemfile_text,
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

        raise GitHubAPIError(
            message="Missing GitHub OAuth scopes",
            detail=(
                "Your current GitHub login is missing the required scope(s): "
                f"{', '.join(missing_scopes)}. Please log out, sign in with GitHub again, and approve the updated permissions."
            ),
            status_code=403,
        )

    @classmethod
    def _resolve_requested_profile(
        cls,
        context: RepositoryContext,
        requested_profile: DeploymentProfile,
    ) -> tuple[ResolvedDeploymentProfile, str]:
        detected_profile, detected_reason = cls._detect_profile(context)

        if requested_profile == "auto":
            return detected_profile, detected_reason

        resolved_profile = requested_profile
        reason = cls._validate_profile_override(context, resolved_profile)
        return resolved_profile, reason

    @classmethod
    def _detect_profile(
        cls,
        context: RepositoryContext,
    ) -> tuple[ResolvedDeploymentProfile, str]:
        next_signal = cls._has_next_signal(context)
        if next_signal:
            if cls._is_next_static_export(context):
                return (
                    "next-static",
                    "Detected Next.js with a static export configuration.",
                )
            raise GitHubAPIError(
                message="Unsupported Next.js repository",
                detail=(
                    "This Next.js repository does not look statically exportable for GitHub Pages. "
                    "Use `output: 'export'` in the Next config or provide a script that runs `next export`."
                ),
                status_code=400,
            )

        if cls._is_jekyll_repository(context):
            return (
                "jekyll",
                "Detected Jekyll configuration files in the repository root.",
            )

        if cls._is_node_static_repository(context):
            return (
                "node-static",
                "Detected a Node-based static site project that can be built before publishing.",
            )

        if cls._is_plain_html_repository(context):
            return (
                "html",
                "Detected plain static site files without a framework build step.",
            )

        raise GitHubAPIError(
            message="Unsupported repository type",
            detail=(
                "DeployBridge could not match this repository to a supported GitHub Pages static-site profile. "
                "Supported profiles in this phase are plain HTML/CSS/JS, Jekyll, Node-based static builds, and static-exportable Next.js."
            ),
            status_code=400,
        )

    @classmethod
    def _validate_profile_override(
        cls,
        context: RepositoryContext,
        profile: ResolvedDeploymentProfile,
    ) -> str:
        if profile == "next-static":
            if not cls._has_next_signal(context):
                raise GitHubAPIError(
                    message="Invalid deployment profile",
                    detail="The selected `next-static` profile requires a Next.js repository.",
                    status_code=400,
                )
            if not cls._is_next_static_export(context):
                raise GitHubAPIError(
                    message="Unsupported Next.js repository",
                    detail=(
                        "The selected `next-static` profile requires static export support. "
                        "Add `output: 'export'` to the Next config or a script that runs `next export`."
                    ),
                    status_code=400,
                )
            return "Manual override selected the Next.js static-export profile."

        if profile == "jekyll":
            if not cls._is_jekyll_repository(context):
                raise GitHubAPIError(
                    message="Invalid deployment profile",
                    detail="The selected `jekyll` profile requires Jekyll configuration files such as `_config.yml`, `_posts`, or a Gemfile with Jekyll.",
                    status_code=400,
                )
            return "Manual override selected the Jekyll profile."

        if profile == "node-static":
            if not cls._is_node_static_repository(context):
                raise GitHubAPIError(
                    message="Invalid deployment profile",
                    detail=(
                        "The selected `node-static` profile requires a Node-based static project with `package.json` and build or generate scripts."
                    ),
                    status_code=400,
                )
            return "Manual override selected the generic Node static-build profile."

        if profile == "html":
            if cls._has_next_signal(context) or cls._is_jekyll_repository(context):
                raise GitHubAPIError(
                    message="Invalid deployment profile",
                    detail=(
                        "The selected `html` profile is only for plain static repositories without a framework build step."
                    ),
                    status_code=400,
                )
            return "Manual override selected the plain HTML/CSS/JS profile."

        raise GitHubAPIError(
            message="Invalid deployment profile",
            detail=f"Unsupported deployment profile: {profile}",
            status_code=400,
        )

    @classmethod
    def _has_next_signal(cls, context: RepositoryContext) -> bool:
        all_dependencies = context.dependencies | context.dev_dependencies
        return (
            "next" in all_dependencies
            or any(candidate in context.root_names for candidate in cls.NEXT_CONFIG_CANDIDATES)
            or any("next " in script.lower() or script.lower().startswith("next") for script in context.scripts.values())
        )

    @classmethod
    def _is_next_static_export(cls, context: RepositoryContext) -> bool:
        script_values = [script.lower() for script in context.scripts.values()]
        if any("next export" in script for script in script_values):
            return True

        next_config_text = context.next_config_text or ""
        if re.search(r"output\s*:\s*[\"']export[\"']", next_config_text):
            return True

        return False

    @classmethod
    def _is_jekyll_repository(cls, context: RepositoryContext) -> bool:
        if "_config.yml" in context.root_names or "_posts" in context.root_directories:
            return True
        gemfile_text = (context.gemfile_text or "").lower()
        return "jekyll" in gemfile_text or "github-pages" in gemfile_text

    @classmethod
    def _is_node_static_repository(cls, context: RepositoryContext) -> bool:
        if not context.package_json:
            return False

        all_dependencies = context.dependencies | context.dev_dependencies
        if cls.SERVER_RUNTIME_MARKERS & all_dependencies and not cls.NODE_STATIC_DEPENDENCY_MARKERS & all_dependencies:
            return False

        if cls.NODE_STATIC_DEPENDENCY_MARKERS & all_dependencies:
            return True

        return "build" in context.scripts or "generate" in context.scripts

    @classmethod
    def _is_plain_html_repository(cls, context: RepositoryContext) -> bool:
        if context.package_json or cls._is_jekyll_repository(context) or cls._has_next_signal(context):
            return False

        static_indicators = {
            "index.html",
            "404.html",
            "styles.css",
            "main.js",
            "app.js",
        }
        if context.root_names & static_indicators:
            return True

        if any(name.endswith((".html", ".css", ".js")) for name in context.root_names):
            return True

        if context.root_directories & {"assets", "static", "css", "js", "images"}:
            return True

        return False

    @classmethod
    def _read_template(cls, template_name: str) -> str:
        template_path = cls.TEMPLATE_DIRECTORY / template_name
        return template_path.read_text(encoding="utf-8")

    @classmethod
    async def _remove_other_workflows(
        cls,
        github_token: str,
        owner: str,
        repository: str,
        default_branch: str,
        keep_filename: str,
    ) -> None:
        headers = cls._build_headers(github_token)
        all_workflows = {
            definition.workflow_filename
            for definition in cls.PROFILE_DEFINITIONS.values()
        }
        stale_workflows = sorted(all_workflows - {keep_filename})

        async with httpx.AsyncClient() as client:
            for workflow_filename in stale_workflows:
                url = cls._workflow_contents_url(owner, repository, workflow_filename)
                get_response = await client.get(url, headers=headers)
                if get_response.status_code != 200:
                    continue

                sha = get_response.json().get("sha")
                if not sha:
                    continue

                payload = {
                    "message": f"DeployBridge: Remove stale {workflow_filename} workflow",
                    "sha": sha,
                    "branch": default_branch,
                }
                delete_response = await client.delete(url, headers=headers, json=payload)
                if delete_response.status_code in (200, 204):
                    print(f"  ✓ Removed stale workflow {workflow_filename}")

    @classmethod
    async def _upsert_workflow(
        cls,
        github_token: str,
        owner: str,
        repository: str,
        default_branch: str,
        profile_definition: DeploymentProfileDefinition,
    ) -> None:
        workflow = cls._read_template(profile_definition.workflow_template).replace(
            "__DEFAULT_BRANCH__",
            default_branch,
        )
        encoded_workflow = base64.b64encode(workflow.encode("utf-8")).decode("utf-8")
        headers = cls._build_headers(github_token)
        url = cls._workflow_contents_url(owner, repository, profile_definition.workflow_filename)

        sha = None
        async with httpx.AsyncClient() as client:
            get_response = await client.get(url, headers=headers)
            if get_response.status_code == 200:
                sha = get_response.json().get("sha")
                if sha:
                    print(f"  Workflow file exists, SHA: {sha[:8]}...")

            payload = {
                "message": f"DeployBridge: Add {profile_definition.key} GitHub Pages workflow",
                "content": encoded_workflow,
                "branch": default_branch,
            }
            if sha:
                payload["sha"] = sha

            print(f"  Creating/updating workflow file {profile_definition.workflow_filename}...")
            response = await client.put(url, headers=headers, json=payload)

        if response.status_code not in (200, 201):
            raise GitHubAPIError(
                message="Failed to create workflow",
                detail=(
                    "GitHub could not create the Pages workflow file. "
                    "If you logged in before the new permissions were added, log out and sign in with GitHub again. "
                    f"GitHub response: {response.text}"
                ),
                status_code=400,
            )

        print("✓ Workflow created/updated successfully")

    @classmethod
    async def _configure_pages(
        cls,
        github_token: str,
        owner: str,
        repository: str,
        default_branch: str,
    ) -> None:
        headers = cls._build_headers(github_token)
        payload = {
            "build_type": "workflow",
            "source": {
                "branch": default_branch,
                "path": "/",
            },
        }

        async with httpx.AsyncClient() as client:
            pages_url = f"{cls.GITHUB_API_BASE_URL}/repos/{owner}/{repository}/pages"
            pages_response = await client.get(pages_url, headers=headers)

            if pages_response.status_code == 404:
                print("  Creating GitHub Pages site...")
                response = await client.post(pages_url, headers=headers, json=payload)
            elif pages_response.status_code == 200:
                print("  Updating existing GitHub Pages site...")
                response = await client.put(pages_url, headers=headers, json=payload)
            else:
                response = pages_response

        if response.status_code in (201, 204):
            print(f"✓ GitHub Pages configured successfully (status: {response.status_code})")
            return

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
        workflow_filename: str,
    ) -> None:
        headers = cls._build_headers(github_token)
        payload = {"ref": default_branch}
        url = (
            f"{cls.GITHUB_API_BASE_URL}/repos/{owner}/{repository}"
            f"/actions/workflows/{workflow_filename}/dispatches"
        )

        print(f'  Triggering workflow_dispatch for "{workflow_filename}" on "{default_branch}"...')

        response = None
        async with httpx.AsyncClient() as client:
            for attempt in range(1, 4):
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code == 204:
                    print("✓ Workflow run triggered successfully")
                    return
                if response.status_code not in (404, 422) or attempt == 3:
                    break
                print(f"  Workflow not ready yet (attempt {attempt}/3). Retrying...")
                await asyncio.sleep(1)

        raise GitHubAPIError(
            message="Failed to start the GitHub Actions workflow",
            detail=response.text if response is not None else "Unknown workflow dispatch error.",
            status_code=400,
        )

    @classmethod
    async def _get_repository_contents(
        cls,
        github_token: str,
        owner: str,
        repository: str,
        path: str,
        ref: str,
    ) -> list[dict[str, Any]]:
        url = f"{cls.GITHUB_API_BASE_URL}/repos/{owner}/{repository}/contents"
        if path:
            url = f"{url}/{path}"

        response = await cls._request(
            method="GET",
            url=url,
            github_token=github_token,
            params={"ref": ref},
        )

        if response.status_code == 404:
            return []
        if response.status_code != 200:
            raise GitHubAPIError(
                message="Unable to inspect repository files",
                detail=f"GitHub returned status code {response.status_code}: {response.text}",
                status_code=400,
            )

        payload = response.json()
        if isinstance(payload, list):
            return payload
        return []

    @classmethod
    async def _get_json_file(
        cls,
        github_token: str,
        owner: str,
        repository: str,
        path: str,
        ref: str,
    ) -> dict[str, Any] | None:
        text = await cls._get_text_file(
            github_token=github_token,
            owner=owner,
            repository=repository,
            path=path,
            ref=ref,
        )
        if not text:
            return None

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise GitHubAPIError(
                message="Invalid package.json",
                detail=f"DeployBridge could not parse `{path}`: {exc}",
                status_code=400,
            ) from exc

    @classmethod
    async def _read_first_available_file(
        cls,
        github_token: str,
        owner: str,
        repository: str,
        ref: str,
        candidates: tuple[str, ...],
    ) -> str | None:
        for candidate in candidates:
            text = await cls._get_text_file(
                github_token=github_token,
                owner=owner,
                repository=repository,
                path=candidate,
                ref=ref,
            )
            if text is not None:
                return text
        return None

    @classmethod
    async def _get_text_file(
        cls,
        github_token: str,
        owner: str,
        repository: str,
        path: str,
        ref: str,
    ) -> str | None:
        url = f"{cls.GITHUB_API_BASE_URL}/repos/{owner}/{repository}/contents/{path}"
        response = await cls._request(
            method="GET",
            url=url,
            github_token=github_token,
            params={"ref": ref},
        )

        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise GitHubAPIError(
                message="Unable to inspect repository files",
                detail=f"GitHub returned status code {response.status_code}: {response.text}",
                status_code=400,
            )

        payload = response.json()
        content = payload.get("content")
        encoding = payload.get("encoding")
        if not content or encoding != "base64":
            return None
        return base64.b64decode(content).decode("utf-8")

    @classmethod
    def _build_headers(cls, github_token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
        }

    @classmethod
    def _workflow_contents_url(
        cls,
        owner: str,
        repository: str,
        workflow_filename: str,
    ) -> str:
        return (
            f"{cls.GITHUB_API_BASE_URL}/repos/{owner}/{repository}"
            f"/contents/.github/workflows/{workflow_filename}"
        )

    @classmethod
    async def _request(
        cls,
        method: str,
        url: str,
        github_token: str,
        **kwargs,
    ) -> httpx.Response:
        headers = cls._build_headers(github_token)
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                **kwargs,
            )
        return response
