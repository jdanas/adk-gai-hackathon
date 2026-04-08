from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import asyncpg
from pgvector.asyncpg import register_vector

from config import get_settings


class AlloyDBConnectionManager:
    def __init__(self) -> None:
        self._pool: asyncpg.Pool | None = None
        self._settings = get_settings()

    async def connect(self) -> asyncpg.Pool:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(
                dsn=self._settings.database_url,
                min_size=1,
                max_size=10,
                init=self._initialize_connection,
            )
        return self._pool

    async def disconnect(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def _initialize_connection(self, connection: asyncpg.Connection) -> None:
        await register_vector(connection)

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[asyncpg.Connection]:
        pool = await self.connect()
        async with pool.acquire() as connection:
            yield connection


db_manager = AlloyDBConnectionManager()
