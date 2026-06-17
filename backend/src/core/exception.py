

class DeployBridgeError(Exception):
    """base exception for the project"""

    def __init__(self, message: str, detail: str = ""):
        self.message = message
        self.detail = detail
        super().__init__(message)


class ConfigGenerationError(DeployBridgeError):
    """failed to generate deployment config"""
    pass