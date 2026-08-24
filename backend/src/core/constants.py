from typing import ClassVar
from functools import lru_cache


class BaseConsts:

    MIN_TOKEN_LENGTH: ClassVar[int] = 20



@lru_cache
def const() -> BaseConsts:
    return BaseConsts()