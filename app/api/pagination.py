from typing import Annotated

from fastapi import Query

LimitParam = Annotated[int, Query(ge=1, le=100)]
OffsetParam = Annotated[int, Query(ge=0)]
