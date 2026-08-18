from typing import Any
from pydantic import BaseModel, Field


class RepositoryInfoRequest(BaseModel):
    """req body for fetching repo information"""
    owner: str = Field(
        ...,
        description="GitHub username or Org name",
        min_length=1,
        max_length=255,
    )

    repository: str = Field(
        ...,
        description="Repository name",
        min_length=1,
        max_length=255,
    )


class RepoBasicInfo(BaseModel):
    """Core repository metadata"""
    id: int | None = None
    name: str = ""
    full_name: str = ""
    description: str | None = None
    html_url: str = ""
    private: bool = False
    visibility: str = "public"

    owner_login: str = ""
    owner_avatar_url: str | None = None

    stars_count: int = 0
    forks_count: int = 0
    watchers_count: int = 0
    open_issues_count: int = 0

    created_at: str | None = None
    updated_at: str | None = None
    pushed_at: str | None = None

    default_branch: str = "main"
    size: int = 0 
    license_name: str | None = None
    topics: list[str] = []

    has_wiki: bool = False
    has_issues: bool = False
    has_projects: bool = False
    has_pages: bool = False
    is_archived: bool = False
    is_disabled: bool = False


class PagesBuildStatus(BaseModel):
    """Latest GitHub pages build information"""
    status: str | None = None
    url: str | None = None
    updated_at: str | None = None
    duration: float | None = None


class DeploymentStatusInfo(BaseModel):
    """GitHub pages deployment status and configuration"""
    enabled: bool = False
    status: str | None = None
    url: str | None = None
    cname: str | None = None
    https_enabled: bool = False
    source_branch: str | None = None
    protected_domain_state: str | None = None

    latest_build: PagesBuildStatus | None = None

    other_platforms: dict[str, bool] = Field(
        default_factory=dict,
        description="Detected deployment configs for other platforms"
    )


class LanguageEntry(BaseModel):
    """single language with bytes and percentage"""
    name: str
    bytes: int = 0
    percentage: float = 0.0
    color: str | None = None


class LanguageInfo(BaseModel):
    """Language breakdown for the repository"""
    languages: list[LanguageEntry] = Field(default_factory=list)
    total_bytes: int = 0
    primary_language: str | None = None


class TechStackInfo(BaseModel):
    """Detected technology stack from project configuration"""
    framework: str | None = None
    build_tool: str | None = None
    package_manager: str | None = None
    runtime: str | None = None
    styling: str | None = None
    testing: list[str] = Field(default_factory=list)
    deployment_profile: str | None = None
    confidence: str = "medium"


class CommitAuthorInfo(BaseModel):
    """Commit author summery"""
    login: str | None = None
    avatar_url: str | None = None
    date: str | None = None


class CommitEntry(BaseModel):
    """Single commit entry for recent history"""
    sha: str = ""
    short_sha: str = ""
    message: str = ""
    author: CommitAuthorInfo = Field(default_factory=CommitAuthorInfo)
    date: str | None = None
    url: str = ""


class CommitsInfo(BaseModel):
    """Recent commit history"""
    commits: list[CommitEntry] = Field(default_factory=list)
    count: int = 0


class ContributorEntry(BaseModel):
    """Single contributor with contributors stats"""
    login: str = ""
    avatar_url: str | None = None
    contributions: int = 0 
    percentage: float = 0.0
    url: str = ""


class ContributorsInfo(BaseModel):
    """Repository contributors informations"""
    contributors: list[ContributorEntry] = Field(default_factory=list)
    total_count: int = 0 


class BranchEntry(BaseModel):
    """Single branch information"""
    name: str = ""
    commit_sha: str = ""
    short_sha: str = ""
    commit_message: str | None = None
    protected: bool = False
    is_default: bool = False


class BranchesInfo(BaseModel):
    """Repo branches information"""
    branches: list[BranchEntry] = Field(default_factory=list)
    default_branch: str = "main"
    total_count: int = 0


class ReadmeInfo(BaseModel):
    """README file content and metadata"""
    content: str | None = None
    filename: str | None = None
    encoding: str = "utf-8"
    size: int = 0
    url : str | None = None
    html_url: str | None = None


class FileTreeEntry(BaseModel):
    """Root-level file or directory entry"""
    name: str = ""
    path: str = ""
    type: str = ""
    size: int | None = None


class FileTreeInfo(BaseModel):
    """Simplified root file tree"""
    files: list[FileTreeEntry] = Field(default_factory=list)
    total_count: int = 0
    has_workflow_files: bool = False
    detected_workflows: list[str] = Field(default_factory=list)


class RepositoryInfoResponse(BaseModel):
    """
    Complete repository information response

    all sections are optional to allow partial data retrieval
    if some API calls fail
    """
    success: bool = True
    message: str = "Repository information retrieved successfully"

    basic_info: RepoBasicInfo | None = None
    deployment_status: DeploymentStatusInfo | None = None
    languages: LanguageInfo | None = None
    tech_stack: TechStackInfo | None = None

    commits: CommitsInfo | None = None
    contributors: ContributorsInfo | None = None
    branches: BranchesInfo | None = None

    readme: ReadmeInfo | None = None
    file_tree: FileTreeInfo | None = None

    fetched_at: str | None = None
    api_calls_made: int = 0
    errors: list[str] = Field(default_factory=list)