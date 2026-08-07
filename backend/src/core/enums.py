from enum import Enum


# all type of enums 

class Environment(str, Enum):
    PRODUCTION = "production"
    LOCAL = "local"
