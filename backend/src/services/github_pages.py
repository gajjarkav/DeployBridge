import asyncio
import base64
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote

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
    selected_branch: str
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
        preferred_branch: str | None = None,
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
            preferred_branch=preferred_branch,
        )

        # NEW: before declaring the repo "unsupported for Pages", check
        # whether Render is the better target. If yes, return a response
        # that carries recommended_platform='render' so the frontend can
        # show a "Deploy to Render instead" CTA instead of an error.
        should_recommend_render, render_reason = cls.detect_render_recommendation(context)
        if should_recommend_render:
            # Special case: if it's a non-static Next.js repo, GitHub Pages
            # previously raised GitHubAPIError("Unsupported Next.js repo").
            # If it's a server-runtime Node repo, it fell into the
            # "Unsupported repository type" branch below. Either way, we
            # now return a structured recommendation instead of 400-ing.
            try:
                detected_profile, _ = cls._detect_profile(context)
            except GitHubAPIError:
                # _detect_profile raises for server-only repos -- that's
                # exactly the case where we want to recommend Render.
                detected_profile = None
            return GitHubPagesDetectResponse(
                detected_profile=detected_profile,
                supported_profiles=cls.SUPPORTED_PROFILES,
                reason=render_reason,
                branch=context.selected_branch,
                recommended_platform="render",
            )

        detected_profile, reason = cls._detect_profile(context)
        return GitHubPagesDetectResponse(
            detected_profile=detected_profile,
            supported_profiles=cls.SUPPORTED_PROFILES,
            reason=reason,
            branch=context.selected_branch,
        )

    @classmethod
    async def build_repository_context(
        cls,
        github_token: str,
        owner: str,
        repository: str,
        preferred_branch: str | None = None,
    ) -> RepositoryContext:
        """Public wrapper around `_build_repository_context`.

        Added so the Render integration can reuse the SAME repository
        inspection code (GitHub API calls, package.json parsing, root
        file enumeration, Next.js config reads) without duplicating the
        ~80 lines of httpx logic. Render's `detect` needs the same
        RepositoryContext to decide runtime/build/start commands, and
        we don't want two copies of "fetch root files + parse
        package.json + read next.config.*" drifting in the codebase.

        Verifies the repo exists, fetches root file listing, parses
        package.json/Gemfile/next.config.*, and returns a frozen-ish
        dataclass the caller can inspect without further GitHub calls.
        """
        repository_data = await cls._verify_repository(
            github_token=github_token,
            owner=owner,
            repository=repository,
        )
        return await cls._build_repository_context(
            github_token=github_token,
            owner=owner,
            repository=repository,
            repository_data=repository_data,
            preferred_branch=preferred_branch,
        )

    @classmethod
    def detect_render_recommendation(
        cls,
        context: "RepositoryContext",
    ) -> tuple[bool, str]:
        """Returns (should_recommend_render, human_reason).

        RenderService calls this from `RenderService.detect` to decide
        whether the repo is a server-side app. The rule is: if the
        package.json deps contain any of `SERVER_RUNTIME_MARKERS`
        (express, fastify, koa, @nestjs/core, hono, socket.io, ...),
        OR there's a requirements.txt with FastAPI/Flask/etc., OR a
        Dockerfile in the root, then Render is the right platform.

        Returns False for static sites (html/jekyll/node-static/
        next-static) -- those keep going through GitHub Pages.
        """
        if (
            "dockerfile" in context.root_names
            or "docker-compose.yml" in context.root_names
            or "docker-compose.yaml" in context.root_names
        ):
            return True, "Docker configuration detected at repository root."

        all_deps = context.dependencies | context.dev_dependencies
        server_markers_hit = sorted(cls.SERVER_RUNTIME_MARKERS & all_deps)
        if server_markers_hit:
            return True, (
                "Server runtime marker(s) detected in package.json dependencies: "
                + ", ".join(server_markers_hit)
                + ". GitHub Pages only supports static sites; this looks like a "
                "long-running server process, which is exactly what Render web "
                "services are designed for."
            )

        # Non-static Next.js (no `output: 'export'`) -> recommend Render.
        if cls._has_next_signal(context) and not cls._is_next_static_export(context):
            return True, (
                "Next.js app detected without a static export configuration. "
                "This needs a Node.js runtime to serve SSR/API routes, so Render "
                "is the right target (GitHub Pages can only host the static export)."
            )

        # Python server runtime: look at requirements.txt-equivalent markers
        # that the RepositoryContext does not parse today; we approximate by
        # looking at README and any *.py files at root for fastapi/flask/django.
        py_root_files = [n for n in context.root_names if n.endswith(".py")]
        if "requirements.txt" in context.root_names or py_root_files:
            return True, (
                "Python project detected (requirements.txt or .py files at "
                "repo root). Render can run Python web services directly; "
                "GitHub Pages cannot."
            )

        return False, "Static site; GitHub Pages is the right platform."

    @classmethod
    async def deploy(
        cls,
        github_token: str,
        owner: str,
        repository: str,
        deployment_profile: DeploymentProfile = "auto",
        preferred_branch: str | None = None,
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
            preferred_branch=preferred_branch,
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
            target_branch=context.selected_branch,
            keep_filename=profile_definition.workflow_filename,
        )
        if context.selected_branch != context.default_branch:
            await cls._remove_other_workflows(
                github_token=github_token,
                owner=owner,
                repository=repository,
                target_branch=context.default_branch,
                keep_filename=None,
            )
        await cls._upsert_workflow(
            github_token=github_token,
            owner=owner,
            repository=repository,
            target_branch=context.selected_branch,
            profile_definition=profile_definition,
        )
        await cls._configure_pages(
            github_token=github_token,
            owner=owner,
            repository=repository,
            target_branch=context.selected_branch,
        )
        await cls._dispatch_workflow(
            github_token=github_token,
            owner=owner,
            repository=repository,
            target_branch=context.selected_branch,
            workflow_filename=profile_definition.workflow_filename,
        )

        print("✓ GitHub Pages deployment completed successfully!\n")

        return GitHubPagesDeployResponse(
            success=True,
            message=(
                f'GitHub Pages deployment started for "{repository}" using the '
                f'"{resolved_profile}" profile on "{context.selected_branch}".'
            ),
            resolved_profile=resolved_profile,
            workflow_template=profile_definition.workflow_template,
            branch=context.selected_branch,
        )

    @classmethod
    async def _verify_repository(
        cls,
        github_token: str,
        owner: str,
        repository: str,
    ) -> dict[str, Any]:
        headers = cls._build_headers(github_token)

        async with httpx.AsyncClient(timeout=30.0) as client:
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
        preferred_branch: str | None = None,
    ) -> RepositoryContext:
        default_branch = repository_data.get("default_branch")
        if not default_branch:
            raise GitHubAPIError(
                message="Repository has no default branch",
                detail="This repository appears to be empty. Add your site files first, then try again.",
                status_code=400,
            )

        selected_branch = preferred_branch.strip() if preferred_branch else default_branch
        if selected_branch != default_branch:
            branch_exists = await cls._branch_exists(
                github_token=github_token,
                owner=owner,
                repository=repository,
                branch=selected_branch,
            )
            if not branch_exists:
                raise GitHubAPIError(
                    message="Saved deploy branch does not exist",
                    detail=(
                        f'The saved deploy branch "{selected_branch}" was not found in '
                        f'"{owner}/{repository}". Clear it in settings or save a valid branch name.'
                    ),
                    status_code=400,
                )

        root_items = await cls._get_repository_contents(
            github_token=github_token,
            owner=owner,
            repository=repository,
            path="",
            ref=selected_branch,
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
            ref=selected_branch,
        )
        next_config_text = await cls._read_first_available_file(
            github_token=github_token,
            owner=owner,
            repository=repository,
            ref=selected_branch,
            candidates=cls.NEXT_CONFIG_CANDIDATES,
        )
        gemfile_text = await cls._get_text_file(
            github_token=github_token,
            owner=owner,
            repository=repository,
            path="Gemfile",
            ref=selected_branch,
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
            selected_branch=selected_branch,
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
    async def _branch_exists(
        cls,
        github_token: str,
        owner: str,
        repository: str,
        branch: str,
    ) -> bool:
        encoded_branch = quote(branch, safe="")
        response = await cls._request(
            method="GET",
            url=f"{cls.GITHUB_API_BASE_URL}/repos/{owner}/{repository}/branches/{encoded_branch}",
            github_token=github_token,
        )

        if response.status_code == 200:
            return True
        if response.status_code == 404:
            return False

        raise GitHubAPIError(
            message="Failed to validate deploy branch",
            detail=f"GitHub returned status code {response.status_code}: {response.text}",
            status_code=400,
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
    def _is_docker_repository(cls, context: RepositoryContext) -> bool:
        return (
            "dockerfile" in context.root_names
            or "docker-compose.yml" in context.root_names
            or "docker-compose.yaml" in context.root_names
        )

    @classmethod
    def _detect_profile(
        cls,
        context: RepositoryContext,
    ) -> tuple[ResolvedDeploymentProfile, str]:
        if cls._is_docker_repository(context):
            raise GitHubAPIError(
                message="Docker repository detected",
                detail=(
                    "DeployBridge detected this is a Docker-based repository (found Dockerfile or docker-compose.yml). "
                    "GitHub Pages only supports static sites. To deploy a Docker application, please use the Render deployment option."
                ),
                status_code=400,
            )

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
        target_branch: str,
        keep_filename: str | None,
    ) -> None:
        headers = cls._build_headers(github_token)
        all_workflows = {
            definition.workflow_filename
            for definition in cls.PROFILE_DEFINITIONS.values()
        }
        keep_filenames = {keep_filename} if keep_filename else set()
        stale_workflows = sorted(all_workflows - keep_filenames)

        async with httpx.AsyncClient(timeout=30.0) as client:
            for workflow_filename in stale_workflows:
                url = cls._workflow_contents_url(owner, repository, workflow_filename)
                get_response = await client.get(
                    url,
                    headers=headers,
                    params={"ref": target_branch},
                )
                if get_response.status_code != 200:
                    continue

                sha = get_response.json().get("sha")
                if not sha:
                    continue

                payload = {
                    "message": f"DeployBridge: Remove stale {workflow_filename} workflow",
                    "sha": sha,
                    "branch": target_branch,
                }
                delete_response = await client.delete(url, headers=headers, json=payload)
                if delete_response.status_code in (200, 204):
                    print(
                        f'  ✓ Removed stale workflow {workflow_filename} from "{target_branch}"'
                    )

    @classmethod
    async def _upsert_workflow(
        cls,
        github_token: str,
        owner: str,
        repository: str,
        target_branch: str,
        profile_definition: DeploymentProfileDefinition,
    ) -> None:
        workflow = cls._read_template(profile_definition.workflow_template).replace(
            "__DEFAULT_BRANCH__",
            target_branch,
        )
        encoded_workflow = base64.b64encode(workflow.encode("utf-8")).decode("utf-8")
        headers = cls._build_headers(github_token)
        url = cls._workflow_contents_url(owner, repository, profile_definition.workflow_filename)

        sha = None
        async with httpx.AsyncClient(timeout=30.0) as client:
            get_response = await client.get(
                url,
                headers=headers,
                params={"ref": target_branch},
            )
            if get_response.status_code == 200:
                sha = get_response.json().get("sha")
                if sha:
                    print(f"  Workflow file exists, SHA: {sha[:8]}...")

            payload = {
                "message": f"DeployBridge: Add {profile_definition.key} GitHub Pages workflow",
                "content": encoded_workflow,
                "branch": target_branch,
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
        target_branch: str,
    ) -> None:
        headers = cls._build_headers(github_token)
        payload = {
            "build_type": "workflow",
            "source": {
                "branch": target_branch,
                "path": "/",
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
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
        target_branch: str,
        workflow_filename: str,
    ) -> None:
        headers = cls._build_headers(github_token)
        payload = {"ref": target_branch}
        url = (
            f"{cls.GITHUB_API_BASE_URL}/repos/{owner}/{repository}"
            f"/actions/workflows/{workflow_filename}/dispatches"
        )

        print(f'  Triggering workflow_dispatch for "{workflow_filename}" on "{target_branch}"...')

        response = None
        async with httpx.AsyncClient(timeout=30.0) as client:
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
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                **kwargs,
            )
        return response


    # ------------------------------------------------------------------
    # Custom domains  (Feature ① — file-based: CNAME file + Pages config)
    #
    # The two platforms are architecturally different — that's the viva gold:
    #
    #   RENDER = platform-managed.  Render stores the domain on its side,
    #           verifies DNS, issues the cert.  Your UI is stateless.
    #
    #   PAGES  = file-based.  The "claim" is a CNAME file committed to the
    #           deploy branch via the SAME Contents API we already use to
    #           upload workflow YAMLs.  GitHub then verifies DNS and offers
    #           "Enforce HTTPS" (auto-issued by Let's Encrypt).
    #
    # Same UX on top, two completely different mechanisms below.
    # ------------------------------------------------------------------

    # GitHub Pages' four A-records for apex domains (kumar.dev, not www.kumar.dev).
    # Hard-coded by GitHub — they don't change often, but the README warns to
    # check GitHub's docs page if cert issuance keeps failing.
    PAGES_APEX_A_RECORDS = [
        "185.199.108.153",
        "185.199.109.153",
        "185.199.110.153",
        "185.199.111.153",
    ]

    @classmethod
    def _is_apex_domain(cls, domain: str, owner: str) -> bool:
        """Heuristic: a domain is apex if it has exactly one label before the
        TLD, OR if it's <owner>.<tld> (the user's own Pages root). Anything with
        more labels is a subdomain.

        Examples:
            kumar.dev           → True  (apex)
            notes.kumar.dev     → False (subdomain → CNAME)
            kumar.github.io     → True  (apex — <owner>.github.io)
            notes.kumar.github.io → False (subdomain)

        DNS rules say an apex can't be a CNAME, so we either use A-records
        or a provider that flattens (Cloudflare).
        """
        # Strip trailing dot.
        clean = domain.rstrip(".")
        # <owner>.github.io is the apex from GitHub's POV.
        if clean == f"{owner.lower()}.github.io":
            return True
        # Heuristic by label count: 2 labels = apex (kumar.dev), 3+ = sub.
        labels = clean.split(".")
        if len(labels) <= 2:
            return True
        # Special case: .github.io "apex" already handled above; 3 labels like
        # notes.kumar.dev = subdomain.
        return False

    @classmethod
    def _derive_pages_dns_records(
        cls,
        domain: str,
        owner: str,
    ) -> tuple[str, str]:
        """Return (record_type, record_name) for the user's DNS provider.

        - Subdomain (notes.kumar.dev) → CNAME, name = "notes"
        - Apex (kumar.dev)             → A,      name = "@"
        """
        if cls._is_apex_domain(domain, owner):
            return "A", "@"
        # Take everything before the apex as the subdomain label.
        # E.g. "notes.kumar.dev" → "notes"; "app.www.kumar.dev" → "app.www"
        # by splitting off the last two labels.
        labels = domain.split(".")
        sub_label = ".".join(labels[:-2]) if len(labels) > 2 else labels[0]
        return "CNAME", sub_label or "@"

    @classmethod
    def _derive_cname_target(cls, domain: str, owner: str) -> str:
        """CNAME target = <owner>.github.io for subdomains. For apex, we
        return the first A-record (the frontend shows all four)."""
        if cls._is_apex_domain(domain, owner):
            return cls.PAGES_APEX_A_RECORDS[0]
        return f"{owner.lower()}.github.io"

    @classmethod
    async def add_custom_domain(
        cls,
        github_token: str,
        owner: str,
        repository: str,
        domain: str,
        branch: str | None = None,
    ) -> "GitHubPagesCustomDomainResponse":
        """Commit a CNAME file containing `domain` to the deploy branch.

        The CNAME file lives at the repo ROOT (not under .github/workflows/).
        Its content is just the bare domain, no newline. GitHub Pages reads
        it on the next build and starts serving the custom domain.

        We also touch the Pages config (PUT /repos/{owner}/{repo}/pages)
        so GitHub knows to look for the CNAME file. The Pages config is
        idempotent — calling it on every add-custom-domain is safe.
        """
        # Resolve the branch (user's saved deploy_branch or repo default).
        if not branch:
            repo_data = await cls._verify_repository(github_token, owner, repository)
            branch = repo_data.get("default_branch", "main")
        else:
            # Validate the user-supplied branch exists.
            exists = await cls._branch_exists(
                github_token=github_token,
                owner=owner,
                repository=repository,
                branch=branch,
            )
            if not exists:
                raise GitHubAPIError(
                    message="Branch does not exist",
                    detail=f'Branch "{branch}" not found in {owner}/{repository}.',
                )

        # 1. Commit (or update) the CNAME file at repo root.
        #    GET first to capture the existing file SHA (required by GitHub for
        #    PUTs to existing files; missing SHA returns 422).
        cname_url = (
            f"{cls.GITHUB_API_BASE_URL}/repos/{owner}/{repository}/"
            f"contents/CNAME?ref={branch}"
        )
        headers = cls._build_headers(github_token)
        existing_sha: str | None = None
        async with httpx.AsyncClient(timeout=30.0) as client:
            get_resp = await client.get(cname_url, headers=headers)
            if get_resp.status_code == 200:
                existing_sha = (get_resp.json() or {}).get("sha")

            payload = {
                "message": f"DeployBridge: set custom domain to {domain}",
                "content": base64.b64encode(domain.encode("utf-8")).decode("utf-8"),
                "branch": branch,
            }
            if existing_sha:
                payload["sha"] = existing_sha

            put_resp = await client.put(cname_url, headers=headers, json=payload)
            if put_resp.status_code not in (200, 201):
                raise GitHubAPIError(
                    message="Failed to commit CNAME file",
                    detail=f"GitHub returned {put_resp.status_code}: {put_resp.text[:500]}",
                )

        # 2. Touch the Pages config so GitHub re-reads the CNAME file.
        await cls._configure_pages(
            github_token=github_token,
            owner=owner,
            repository=repository,
            target_branch=branch,
        )

        # 3. Build the DNS instruction card the frontend will show.
        record_type, record_name = cls._derive_pages_dns_records(domain, owner)
        cname_target = cls._derive_cname_target(domain, owner)

        # Importing here to avoid a top-level circular import; this method
        # is only invoked through the API layer.
        from ...schemas.github_pages import GitHubPagesCustomDomainResponse, GitHubPagesCustomDomainStatus

        status: GitHubPagesCustomDomainStatus = "waiting_for_dns"
        message = (
            f"CNAME file committed to {branch}. Add the following DNS record at "
            f"your registrar — GitHub will verify DNS and issue a TLS cert "
            f"automatically (usually 5–15 minutes)."
        )
        if record_type == "A":
            message += (
                " Use all four A-records: " + ", ".join(cls.PAGES_APEX_A_RECORDS) + "."
            )

        return GitHubPagesCustomDomainResponse(
            domain=domain,
            branch=branch,
            cname_target=cname_target,
            record_type=record_type,
            record_name=record_name,
            https_enabled=False,
            status=status,
            message=message,
        )

    @classmethod
    async def verify_custom_domain(
        cls,
        github_token: str,
        owner: str,
        repository: str,
        domain: str,
        branch: str | None = None,
    ) -> "GitHubPagesCustomDomainResponse":
        """Check GitHub's Pages config for `cname` + `https_enforced` status.

        Three possible states:
          - cname not present or doesn't match → user's CNAME file write failed;
            tell them to re-check.
          - cname matches but https_enforced=False → DNS verified, cert
            issuance in progress. Try enabling HTTPS.
          - https_enforced=True → cert issued; status=live.
        """
        if not branch:
            repo_data = await cls._verify_repository(github_token, owner, repository)
            branch = repo_data.get("default_branch", "main")

        headers = cls._build_headers(github_token)
        pages_url = f"{cls.GITHUB_API_BASE_URL}/repos/{owner}/{repository}/pages"
        async with httpx.AsyncClient(timeout=30.0) as client:
            get_resp = await client.get(pages_url, headers=headers)
            if get_resp.status_code != 200:
                raise GitHubAPIError(
                    message="Pages not configured",
                    detail="GitHub Pages hasn't been enabled on this repo yet. "
                           "Deploy the repo to Pages first, then add a custom domain.",
                )
            pages_data = get_resp.json() or {}
            current_cname = pages_data.get("cname") or ""
            https_enforced = bool(pages_data.get("https_enforced"))
            https_possible = bool(pages_data.get("https"))

        from ...schemas.github_pages import GitHubPagesCustomDomainResponse, GitHubPagesCustomDomainStatus

        record_type, record_name = cls._derive_pages_dns_records(domain, owner)
        cname_target = cls._derive_cname_target(domain, owner)

        # DNS propagation can take minutes to hours. If GitHub hasn't seen
        # the CNAME resolve yet, the `cname` field will still be set (we
        # wrote it to the file), but `https` will be False.
        status: GitHubPagesCustomDomainStatus
        if current_cname.strip().lower() != domain.strip().lower():
            # CNAME file write appears to have failed OR GitHub hasn't
            # processed it. Tell the user to wait + re-check.
            status = "waiting_for_dns"
            message = (
                f"GitHub hasn't seen the CNAME file (current cname on the Pages "
                f"site is '{current_cname or '<none>'}'). Confirm the CNAME file "
                f"is committed to branch '{branch}' and a Pages build has run."
            )
            https_enforced = False
        elif https_enforced:
            status = "live"
            message = (
                f"🔒 Verified and HTTPS enforced. The site is live at "
                f"https://{domain}."
            )
        elif https_possible:
            # Cert is available — try to enable HTTPS enforcement now.
            enabled = await cls._enable_pages_https(github_token, owner, repository)
            status = "live" if enabled else "verified"
            message = (
                "TLS cert is available. HTTPS enforcement "
                + ("enabled — site is live." if enabled else "could not be enabled automatically; toggle it in the GitHub UI.")
            )
            https_enforced = enabled
        else:
            status = "verified"
            message = (
                "DNS verified. GitHub is issuing the Let's Encrypt cert — "
                "re-check in a few minutes."
            )

        return GitHubPagesCustomDomainResponse(
            domain=domain,
            branch=branch,
            cname_target=cname_target,
            record_type=record_type,
            record_name=record_name,
            https_enabled=https_enforced,
            status=status,
            message=message,
        )

    @classmethod
    async def _enable_pages_https(cls, github_token: str, owner: str, repository: str) -> bool:
        """PUT /repos/{owner}/{repo}/pages with `https_enforced: true`.

        Returns True on success, False otherwise. Idempotent — calling when
        HTTPS is already enforced still returns True.
        """
        headers = cls._build_headers(github_token)
        pages_url = f"{cls.GITHUB_API_BASE_URL}/repos/{owner}/{repository}/pages"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.put(pages_url, headers=headers, json={"https_enforced": True})
            return resp.status_code in (200, 204)
