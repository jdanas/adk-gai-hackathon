from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

import asyncpg
from google.cloud.alloydbconnector import AsyncConnector
from pgvector.asyncpg import register_vector

from config import get_settings


class AlloyDBConnectionManager:
    def __init__(self) -> None:
        self._pool: asyncpg.Pool | None = None
        self._connector: AsyncConnector | None = None
        self._settings = get_settings()

    async def connect(self) -> asyncpg.Pool:
        if self._pool is None:
            if self._settings.alloydb_instance_uri:
                self._connector = AsyncConnector(
                    refresh_strategy="lazy",
                    ip_type=self._settings.alloydb_ip_type.upper(),
                )
                self._pool = await asyncpg.create_pool(
                    self._settings.alloydb_instance_uri,
                    min_size=1,
                    max_size=10,
                    init=self._initialize_connection,
                    connect=self._connect_with_connector,
                )
            else:
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
        if self._connector is not None:
            await self._connector.close()
            self._connector = None

    async def _initialize_connection(self, connection: asyncpg.Connection) -> None:
        await register_vector(connection)

    async def _connect_with_connector(
        self,
        instance_uri: str,
        **kwargs: object,
    ) -> asyncpg.Connection:
        if self._connector is None:
            raise RuntimeError("AlloyDB connector was not initialized.")

        connect_kwargs = {
            "user": self._settings.alloydb_user,
            "db": self._settings.alloydb_database,
            "ip_type": self._settings.alloydb_ip_type.upper(),
        }
        if self._settings.alloydb_enable_iam_auth:
            connect_kwargs["enable_iam_auth"] = True
        else:
            connect_kwargs["password"] = self._settings.alloydb_password

        return await self._connector.connect(
            instance_uri,
            "asyncpg",
            **connect_kwargs,
        )

    @asynccontextmanager
    async def acquire(self) -> AsyncIterator[asyncpg.Connection]:
        pool = await self.connect()
        async with pool.acquire() as connection:
            yield connection


db_manager = AlloyDBConnectionManager()
