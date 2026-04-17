"""FastAPI dependency providers."""

from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession


async def get_db_session(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Yield a database session for the duration of one request.

    Usage:
        @router.get("/foo")
        async def foo(session: AsyncSession = Depends(get_db_session)):
            ...
    """
    db = request.app.state.db
    async with db.session() as session:
        yield session
