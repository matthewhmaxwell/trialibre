"""SQLAlchemy async database engine and session management."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from ctm.config import DatabaseBackend, DatabaseConfig


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all ORM models."""

    pass


class Database:
    """Async database connection manager.

    Supports both SQLite (single-user desktop) and PostgreSQL (enterprise).
    """

    def __init__(self, config: DatabaseConfig) -> None:
        self.config = config
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    @property
    def url(self) -> str:
        """Construct the database URL from config."""
        if self.config.backend == DatabaseBackend.POSTGRESQL:
            if self.config.postgresql_url:
                return self.config.postgresql_url
            raise ValueError("PostgreSQL URL not configured")
        # SQLite with aiosqlite driver
        return f"sqlite+aiosqlite:///{self.config.sqlite_path}"

    async def connect(self) -> None:
        """Initialize the database engine and session factory."""
        engine_kwargs: dict = {"echo": self.config.echo}

        if self.config.backend == DatabaseBackend.SQLITE:
            # SQLite-specific: enable WAL mode for better concurrency
            engine_kwargs["connect_args"] = {"check_same_thread": False}

        self._engine = create_async_engine(self.url, **engine_kwargs)
        self._session_factory = async_sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )

        # Create tables
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Enable WAL mode for SQLite
        if self.config.backend == DatabaseBackend.SQLITE:
            async with self._engine.begin() as conn:
                await conn.exec_driver_sql("PRAGMA journal_mode=WAL")
                await conn.exec_driver_sql("PRAGMA busy_timeout=5000")

    async def disconnect(self) -> None:
        """Close the database engine."""
        if self._engine:
            await self._engine.dispose()
            self._engine = None
            self._session_factory = None

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get an async database session."""
        if self._session_factory is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
