from typing import ClassVar
from functools import lru_cache


class BaseConsts:

    MIN_TOKEN_LENGTH: ClassVar[int] = 20

    FERNET_TOKEN_PREFIX: ClassVar[str] = "gAAAA"



@lru_cache
def const() -> BaseConsts:
    return BaseConsts()