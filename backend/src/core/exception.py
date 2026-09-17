

class DeployBridgeError(Exception):
    """base exception for the project"""

    def __init__(self, message: str, detail: str = "", status_code: int = 400):
        self.message = message
        self.detail = detail
        self.status_code = status_code
        super().__init__(message)


class ConfigGenerationError(DeployBridgeError):
    """failed to generate deployment config"""
    pass



class GitHubPagesError(DeployBridgeError):
    """Base exception for GitHub Pages deployment"""
    pass

class RepositoryNotFoundError(GitHubPagesError):
    """Repository was not found or access was denied"""

    def __init__(self, message: str, detail: str = ""):
        super().__init__(message=message, detail=detail, status_code=404)

class GitHubAPIError(GitHubPagesError):
    """Unexpected response from GitHub API"""

    def __init__(self, message: str, detail: str = "", status_code: int = 400):
        super().__init__(message=message, detail=detail, status_code=status_code)


class RenderError(DeployBridgeError):
    """
    Base exception for Render integration failures.

    Mirrors GitHubPagesError so the api/v1/render.py handlers can use the
    same try/except pattern as github_pages.py: catch RenderError, surface
    `exc.detail or exc.message` to the user, and use `exc.status_code` as
    the HTTP status (defaults to 400, callers raise with 401/402/404/429
    where appropriate).
    """
    pass