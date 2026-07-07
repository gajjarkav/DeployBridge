

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
