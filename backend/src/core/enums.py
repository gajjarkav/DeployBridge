from enum import Enum

class Environment(str, Enum):
    PRODUCTION = "production"
    LOCAL = "local"