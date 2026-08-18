import asyncio
import base64
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import HTTPException, status

from src.core.config import get_settings
from src.schemas.repo_info import (
    BranchEntry,
    BranchesInfo,
    CommitAuthorInfo,
    CommitEntry,
    CommitsInfo,
    ContributorEntry,
    ContributorsInfo,
    DeploymentStatusInfo,
    FileTreeEntry,
    FileTreeInfo,
    LanguageEntry,
    LanguageInfo,
    PagesBuildStatus,
    ReadmeInfo,
    RepoBasicInfo,
    RepositoryInfoResponse,
    TechStackInfo,
)


settings = get_settings()

class GitHubService:

    TOKEN_URL = "https://github.com/login/oauth/access_token"
    USER_API_URL = "https://api.github.com/user"
    EMAILS_API_URL = "https://api.github.com/user/emails"
    GITHUB_API_BASE_URL = "https://api.github.com"


    PLATFORM_CONFIG_FILES = {
        "vercel": "vercel.json",
        "netlify": "netlify.toml",
        "railway": "railway.json",
        "render": "render.yaml",
        "heroku": "Procfile",
        "docker": "Dockerfile",
    }
        

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


    @classmethod
    def _get_auth_headers(cls, token: str) -> dict[str, str]:
        """build standard GitHub authorization headers"""
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
        }

    @classmethod
    async def _fetch_github_api(
        cls,
        client: httpx.AsyncClient,
        url: str,
        headers: dict[str, str],
    ) -> tuple[Any | None, str | None]:
        """
        Fetch a GitHub API endpoint safely

        Returns:
            Tuple of (data, error_message)
            - On success: (parsed_json, None)
            - On failure: (None, error_description)
        """
        try:
            response = await client.get(url, headers=headers, timeout=10.0)

            if response.status_code == 200:
                return response.json(), None
            elif response.status_code == 404:
                return None, f"Resource not found (404): {url}"
            elif response.status_code == 403:
                return None, f"Access forbidden (403) - rate limit or permissions issue"
            elif response.status_code == 401:
                return None, f"Unauthorized (401) - token may be invalid"
            else:
                return None, f"API error ({response.status_code}): {url}"

        except httpx.TimeoutException:
            return None, f"Request timeout: {url}"
        except Exception as e:
            return None, f"Unexpected error: {str(e)}"

    
    @classmethod
    async def _fetch_basic_info(
        cls,
        client: httpx.AsyncClient,
        headers: dict[str, str],
        owner: str,
        repo: str,
    ) -> RepoBasicInfo:
        """Fetch and format basic repository information"""
        url = f"{cls.GITHUB_API_BASE_URL}/repos/{owner}/{repo}"
        data, error = await cls._fetch_github_api(client, url, headers)

        if error or not data:
            return RepoBasicInfo()

        license_name = None
        if data.get("license"):
            license_name = data["license"].get("spdx_id")
            if license_name == "NOASSERTION":
                license_name = None

        return RepoBasicInfo(
            id=data.get("id"),
            name=data.get("name", ""),
            full_name=data.get("full_name", ""),
            description=data.get("description"),
            html_url=data.get("html_url", ""),
            private=data.get("private", False),
            visibility=data.get("visibility", "public").capitalize(),
            owner_login=data.get("owner", {}).get("login", "") if data.get("owner") else "",
            owner_avatar_url=data.get("owner", {}).get("avatar_url") if data.get("owner") else None,
            stars_count=data.get("stargazers_count", 0),
            forks_count=data.get("forks_count", 0),
            watchers_count=data.get("watchers_count", 0),
            open_issues_count=data.get("open_issues_count", 0),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
            pushed_at=data.get("pushed_at"),
            default_branch=data.get("default_branch", "main"),
            size=data.get("size", 0),
            license_name=license_name,
            topics=data.get("topics", []),
            has_wiki=data.get("has_wiki", False),
            has_issues=data.get("has_issues", False),
            has_projects=data.get("has_projects", False),
            has_pages=data.get("has_pages", False),
            is_archived=data.get("archived", False),
            is_disabled=data.get("disabled", False),
        )

    @classmethod
    async def _fetch_deployment_status(
        cls,
        client: httpx.AsyncClient,
        headers: dict[str, str],
        owner: str,
        repo: str,
    ) -> DeploymentStatusInfo:
        """Fetch GitHub Pages deployment status."""
        url = f"{cls.GITHUB_API_BASE_URL}/repos/{owner}/{repo}/pages"
        data, error = await cls._fetch_github_api(client, url, headers)
        
        deployment_status = DeploymentStatusInfo()
        
        if not error and data:
            deployment_status.enabled = True
            deployment_status.status = data.get("status")
            deployment_status.url = data.get("html_url")
            deployment_status.cname = data.get("cname")
            deployment_status.https_enabled = data.get("https_enforced", False)
            deployment_status.protected_domain_state = data.get("protected_domain_state")
            
            source = data.get("source", {})
            if source:
                deployment_status.source_branch = source.get("branch")
            
            builds_url = f"{cls.GITHUB_API_BASE_URL}/repos/{owner}/{repo}/pages/builds?per_page=1"
            builds_data, builds_error = await cls._fetch_github_api(client, builds_url, headers)
            
            if not builds_error and builds_data and len(builds_data) > 0:
                latest_build = builds_data[0]
                
                duration_min = None
                if latest_build.get("created_at") and latest_build.get("updated_at"):
                    try:
                        start = datetime.fromisoformat(latest_build["created_at"].replace("Z", "+00:00"))
                        end = datetime.fromisoformat(latest_build["updated_at"].replace("Z", "+00:00"))
                        duration_min = (end - start).total_seconds() / 60
                    except (ValueError, TypeError):
                        pass
                
                deployment_status.latest_build = PagesBuildStatus(
                    status=latest_build.get("status"),
                    url=latest_build.get("url"),
                    updated_at=latest_build.get("updated_at"),
                    duration=round(duration_min, 2) if duration_min else None,
                )
        
        contents_url = f"{cls.GITHUB_API_BASE_URL}/repos/{owner}/{repo}/contents/"
        contents_data, _ = await cls._fetch_github_api(client, contents_url, headers)
        
        if contents_data and isinstance(contents_data, list):
            filenames = [item.get("name", "") for item in contents_data]
            detected_platforms = {}
            
            for platform, config_file in cls.PLATFORM_CONFIG_FILES.items():
                if config_file in filenames:
                    detected_platforms[platform] = True
            
            deployment_status.other_platforms = detected_platforms
        
        return deployment_status

    @classmethod
    async def _fetch_languages(
        cls,
        client: httpx.AsyncClient,
        headers: dict[str, str],
        owner: str,
        repo: str,
    ) -> LanguageInfo:
        """Fetch repository language breakdown with percentages."""
        url = f"{cls.GITHUB_API_BASE_URL}/repos/{owner}/{repo}/languages"
        data, error = await cls._fetch_github_api(client, url, headers)
        
        languages_info = LanguageInfo()
        
        if not error and data:
            total_bytes = sum(data.values())
            languages_info.total_bytes = total_bytes
            
            sorted_languages = sorted(data.items(), key=lambda x: x[1], reverse=True)
            
            language_entries = []
            for lang_name, bytes_count in sorted_languages:
                percentage = round((bytes_count / total_bytes * 100), 2) if total_bytes > 0 else 0
                
                language_entries.append(LanguageEntry(
                    name=lang_name,
                    bytes=bytes_count,
                    percentage=percentage,
                    color=None,
                ))
            
            languages_info.languages = language_entries
            
            if language_entries:
                languages_info.primary_language = language_entries[0].name
        
        return languages_info

    @classmethod
    async def _fetch_commits(
        cls,
        client: httpx.AsyncClient,
        headers: dict[str, str],
        owner: str,
        repo: str,
        per_page: int = 5,
    ) -> CommitsInfo:
        """Fetch recent commit history."""
        url = f"{cls.GITHUB_API_BASE_URL}/repos/{owner}/{repo}/commits?per_page={per_page}"
        data, error = await cls._fetch_github_api(client, url, headers)
        
        commits_info = CommitsInfo()
        
        if not error and data:
            commits_info.count = len(data)
            
            for commit_data in data:
                sha = commit_data.get("sha", "")
                commit_detail = commit_data.get("commit", {})
                author_detail = commit_detail.get("author", {})
                committer = commit_data.get("author")
                
                message = commit_detail.get("message", "").split("\n")[0]
                
                commits_info.commits.append(CommitEntry(
                    sha=sha,
                    short_sha=sha[:7] if sha else "",
                    message=message,
                    author=CommitAuthorInfo(
                        login=committer.get("login") if committer else None,
                        avatar_url=committer.get("avatar_url") if committer else None,
                        date=author_detail.get("date"),
                    ),
                    date=author_detail.get("date"),
                    url=commit_data.get("html_url", ""),
                ))
        
        return commits_info

    @classmethod
    async def _fetch_contributors(
        cls,
        client: httpx.AsyncClient,
        headers: dict[str, str],
        owner: str,
        repo: str,
        max_contributors: int = 10,
    ) -> ContributorsInfo:
        """Fetch repository contributors with contribution stats."""
        url = f"{cls.GITHUB_API_BASE_URL}/repos/{owner}/{repo}/contributors?per_page={max_contributors}"
        data, error = await cls._fetch_github_api(client, url, headers)
        
        contributors_info = ContributorsInfo()
        
        if not error and data:
            contributors_info.total_count = len(data)
            
            total_contributions = sum(c.get("contributions", 0) for c in data)
            
            for contrib_data in data:
                contributions = contrib_data.get("contributions", 0)
                percentage = round((contributions / total_contributions * 100), 1) if total_contributions > 0 else 0
                
                contributors_info.contributors.append(ContributorEntry(
                    login=contrib_data.get("login", ""),
                    avatar_url=contrib_data.get("avatar_url"),
                    contributions=contributions,
                    percentage=percentage,
                    url=contrib_data.get("html_url", ""),
                ))
        
        return contributors_info

    @classmethod
    async def _fetch_branches(
        cls,
        client: httpx.AsyncClient,
        headers: dict[str, str],
        owner: str,
        repo: str,
        default_branch: str = "main",
    ) -> BranchesInfo:
        """Fetch repository branches list."""
        url = f"{cls.GITHUB_API_BASE_URL}/repos/{owner}/{repo}/branches?per_page=20"
        data, error = await cls._fetch_github_api(client, url, headers)
        
        branches_info = BranchesInfo(default_branch=default_branch)
        
        if not error and data:
            branches_info.total_count = len(data)
            
            for branch_data in data:
                branch_name = branch_data.get("name", "")
                commit_obj = branch_data.get("commit", {})
                
                sha = commit_obj.get("sha", "")
                
                branches_info.branches.append(BranchEntry(
                    name=branch_name,
                    commit_sha=sha,
                    short_sha=sha[:7] if sha else "",
                    commit_message=None,
                    protected=branch_data.get("protected", False),
                    is_default=(branch_name == default_branch),
                ))
        
        return branches_info

    @classmethod
    async def _fetch_readme(
        cls,
        client: httpx.AsyncClient,
        headers: dict[str, str],
        owner: str,
        repo: str,
    ) -> ReadmeInfo:
        """Fetch and decode README content."""
        url = f"{cls.GITHUB_API_BASE_URL}/repos/{owner}/{repo}/readme"
        data, error = await cls._fetch_github_api(client, url, headers)
        
        readme_info = ReadmeInfo()
        
        if not error and data:
            content_base64 = data.get("content", "")
            
            try:
                decoded_content = base64.b64decode(content_base64).decode("utf-8")
                readme_info.content = decoded_content
            except Exception:
                readme_info.content = "[Error decoding README content]"
            
            readme_info.filename = data.get("name")
            readme_info.size = data.get("size", 0)
            readme_info.url = data.get("download_url")
            readme_info.html_url = data.get("html_url")
        
        return readme_info

    @classmethod
    async def _fetch_file_tree(
        cls,
        client: httpx.AsyncClient,
        headers: dict[str, str],
        owner: str,
        repo: str,
    ) -> FileTreeInfo:
        """Fetch simplified root-level file tree."""
        url = f"{cls.GITHUB_API_BASE_URL}/repos/{owner}/{repo}/contents/"
        data, error = await cls._fetch_github_api(client, url, headers)
        
        file_tree_info = FileTreeInfo()
        
        if not error and data and isinstance(data, list):
            file_tree_info.total_count = len(data)
            
            workflow_files = []
            
            for item in data:
                entry = FileTreeEntry(
                    name=item.get("name", ""),
                    path=item.get("path", ""),
                    type=item.get("type", "file"),
                    size=item.get("size"),
                )
                file_tree_info.files.append(entry)
                
                if item.get("type") == "dir" and item.get("name") == ".github":
                    workflow_files.append(".github/ directory present")
                elif item.get("name", "").endswith((".yml", ".yaml")):
                    if "workflow" in item.get("path", "").lower():
                        workflow_files.append(item.get("name", ""))
            
            if workflow_files:
                file_tree_info.has_workflow_files = True
                file_tree_info.detected_workflows = workflow_files[:5]
        
        return file_tree_info

    @classmethod
    async def detect_tech_stack_simple(
        cls,
        client: httpx.AsyncClient,
        headers: dict[str, str],
        owner: str,
        repo: str,
    ) -> TechStackInfo:
        """
        Simple tech stack detection based on common config files.
        This is a lightweight version - your existing github_pages.py 
        detection can be integrated later for more accuracy.
        """
        tech_stack = TechStackInfo()
        
        pkg_url = f"{cls.GITHUB_API_BASE_URL}/repos/{owner}/{repo}/contents/package.json"
        pkg_data, _ = await cls._fetch_github_api(client, pkg_url, headers)
        
        if pkg_data and pkg_data.get("content"):
            try:
                pkg_content = base64.b64decode(pkg_data["content"]).decode("utf-8")
                import json
                pkg_json = json.loads(pkg_content)
                
                dependencies = {
                    **pkg_json.get("dependencies", {}),
                    **pkg_json.get("devDependencies", {}),
                }
                
                framework_checks = [
                    ("react", "React"),
                    ("next", "Next.js"),
                    ("vue", "Vue.js"),
                    ("angular", "Angular"),
                    ("svelte", "Svelte"),
                    ("express", "Express.js"),
                    ("fastify", "Fastify"),
                ]
                
                for dep_key, framework_name in framework_checks:
                    if any(dep_key.lower() in dep.lower() for dep in dependencies.keys()):
                        tech_stack.framework = framework_name
                        break
                
                build_checks = [
                    ("vite", "Vite"),
                    ("webpack", "Webpack"),
                    ("rollup", "Rollup"),
                    ("parcel", "Parcel"),
                    ("esbuild", "esbuild"),
                    ("turbo", "Turbopack"),
                ]
                
                for build_key, build_name in build_checks:
                    if any(build_key.lower() in dep.lower() for dep in dependencies.keys()):
                        tech_stack.build_tool = build_name
                        break
                
                style_checks = [
                    ("tailwindcss", "Tailwind CSS"),
                    ("styled-components", "Styled Components"),
                    ("sass", "Sass/SCSS"),
                    ("less", "Less"),
                    ("css-modules", "CSS Modules"),
                ]
                
                testing_tools = []
                test_checks = [
                    ("jest", "Jest"),
                    ("vitest", "Vitest"),
                    ("mocha", "Mocha"),
                    ("cypress", "Cypress"),
                    ("playwright", "Playwright"),
                    ("testing-library", "Testing Library"),
                ]
                
                for test_key, test_name in test_checks:
                    if any(test_key.lower() in dep.lower() for dep in dependencies.keys()):
                        testing_tools.append(test_name)
                
                tech_stack.testing = testing_tools[:4]
                tech_stack.runtime = "Node.js"
                tech_stack.confidence = "medium"
                
            except (json.JSONDecodeError, UnicodeDecodeError, TypeError):
                pass
        
        python_files = ["requirements.txt", "pyproject.toml", "setup.py"]
        for py_file in python_files:
            py_url = f"{cls.GITHUB_API_BASE_URL}/repos/{owner}/{repo}/contents/{py_file}"
            py_data, _ = await cls._fetch_github_api(client, py_url, headers)
            
            if py_data:
                tech_stack.runtime = "Python"
                if not tech_stack.framework:
                    if py_data.get("content"):
                        try:
                            content = base64.b64decode(py_data["content"]).decode("utf-8").lower()
                            if "django" in content:
                                tech_stack.framework = "Django"
                                tech_stack.confidence = "high"
                            elif "flask" in content:
                                tech_stack.framework = "Flask"
                                tech_stack.confidence = "high"
                            elif "fastapi" in content:
                                tech_stack.framework = "FastAPI"
                                tech_stack.confidence = "high"
                        except Exception:
                            pass
                break
        
        go_url = f"{cls.GITHUB_API_BASE_URL}/repos/{owner}/{repo}/contents/go.mod"
        go_data, _ = await cls._fetch_github_api(client, go_url, headers)
        if go_data:
            tech_stack.runtime = "Go"
            tech_stack.confidence = "high"
        
        rust_url = f"{cls.GITHUB_API_BASE_URL}/repos/{owner}/{repo}/contents/Cargo.toml"
        rust_data, _ = await cls._fetch_github_api(client, rust_url, headers)
        if rust_data:
            tech_stack.runtime = "Rust"
            tech_stack.confidence = "high"
        
        for java_file in ["pom.xml", "build.gradle", "build.gradle.kts"]:
            java_url = f"{cls.GITHUB_API_BASE_URL}/repos/{owner}/{repo}/contents/{java_file}"
            java_data, _ = await cls._fetch_github_api(client, java_url, headers)
            if java_data:
                tech_stack.runtime = "Java"
                tech_stack.build_tool = "Maven" if java_file == "pom.xml" else "Gradle"
                break
        
        lockfile_checks = [
            ("package-lock.json", "npm"),
            ("yarn.lock", "Yarn"),
            ("pnpm-lock.yaml", "pnpm"),
            ("bun.lockb", "Bun"),
        ]
        
        for lockfile, manager_name in lockfile_checks:
            lock_url = f"{cls.GITHUB_API_BASE_URL}/repos/{owner}/{repo}/contents/{lockfile}"
            lock_data, _ = await cls._fetch_github_api(client, lock_url, headers)
            if lock_data:
                tech_stack.package_manager = manager_name
                break
        
        return tech_stack

    @classmethod
    async def get_repository_info(cls, token: str, owner: str, repo: str) -> RepositoryInfoResponse:
        """
        Main method to fetch comprehensive repository information.
        
        Makes parallel API calls to GitHub for optimal performance.
        Returns structured response with all available information.
        """
        errors = []
        api_calls_made = 0
        
        headers = cls._get_auth_headers(token)
        
        async with httpx.AsyncClient() as client:
            basic_info = await cls._fetch_basic_info(client, headers, owner, repo)
            api_calls_made += 1
            
            if not basic_info.name:
                return RepositoryInfoResponse(
                    success=False,
                    message=f"Repository '{owner}/{repo}' not found or access denied",
                    errors=["Repository not accessible"],
                    fetched_at=datetime.now(timezone.utc).isoformat(),
                    api_calls_made=1,
                )
            
            default_branch = basic_info.default_branch or "main"
            
            results = await asyncio.gather(
                cls._fetch_deployment_status(client, headers, owner, repo),
                cls._fetch_languages(client, headers, owner, repo),
                cls._fetch_commits(client, headers, owner, repo),
                cls._fetch_contributors(client, headers, owner, repo),
                cls._fetch_branches(client, headers, owner, repo, default_branch),
                cls._fetch_readme(client, headers, owner, repo),
                cls._fetch_file_tree(client, headers, owner, repo),
                cls.detect_tech_stack_simple(client, headers, owner, repo),
                return_exceptions=True,
            )
            
            (
                deployment_status,
                languages,
                commits,
                contributors,
                branches,
                readme,
                file_tree,
                tech_stack,
            ) = results[:8]
            
            api_calls_made += 8
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    errors.append(f"Error in fetch operation {i}: {str(result)}")
        
        return RepositoryInfoResponse(
            success=True,
            message="Repository information retrieved successfully",
            basic_info=basic_info,
            deployment_status=deployment_status if not isinstance(deployment_status, Exception) else None,
            languages=languages if not isinstance(languages, Exception) else None,
            tech_stack=tech_stack if not isinstance(tech_stack, Exception) else None,
            commits=commits if not isinstance(commits, Exception) else None,
            contributors=contributors if not isinstance(contributors, Exception) else None,
            branches=branches if not isinstance(branches, Exception) else None,
            readme=readme if not isinstance(readme, Exception) else None,
            file_tree=file_tree if not isinstance(file_tree, Exception) else None,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            api_calls_made=api_calls_made,
            errors=errors if errors else [],
        )     