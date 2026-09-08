from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import monotonic
from typing import Any, cast

from sqlalchemy import event
from sqlalchemy.exc import TimeoutError
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import ConnectionPoolEntry

from chat_service.contracts.database import AcquisitionOutcome
from chat_service.core.database_metrics import DatabaseMetrics
from chat_service.core.settings import Settings


def create_primary_engine(settings: Settings, metrics: DatabaseMetrics) -> AsyncEngine:
    engine = create_async_engine(
        settings.db_primary_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_pool_max_overflow,
        pool_timeout=settings.db_pool_timeout_seconds,
        pool_pre_ping=True,
        connect_args={
            "timeout": settings.db_connect_timeout_seconds,
            "server_settings": {
                "application_name": settings.app_name,
                "statement_timeout": str(settings.db_statement_timeout_ms),
                "lock_timeout": str(settings.db_lock_timeout_ms),
            },
        },
        hide_parameters=True,
    )

    @event.listens_for(engine.sync_engine, "checkout")
    def checkout(connection: Any, record: ConnectionPoolEntry, proxy: Any) -> None:
        cast(dict[str, Any], record.record_info)["checkout_started"] = monotonic()
        metrics.record(metrics.connections.inc)

    @event.listens_for(engine.sync_engine, "checkin")
    @event.listens_for(engine.sync_engine, "detach")
    def returned(connection: Any, record: ConnectionPoolEntry) -> None:
        started = cast(dict[str, Any], record.record_info).pop("checkout_started", None)
        if started is not None:
            metrics.record(metrics.connections.dec)
            metrics.record(lambda: metrics.hold.observe(monotonic() - started))

    return engine


@asynccontextmanager
async def primary_session(
    factory: async_sessionmaker[AsyncSession], metrics: DatabaseMetrics
) -> AsyncIterator[AsyncSession]:
    metrics.record(metrics.sessions.inc)
    try:
        async with factory() as session:
            yield session
    finally:
        metrics.record(metrics.sessions.dec)


async def acquire_primary_connection(
    session: AsyncSession, metrics: DatabaseMetrics
) -> AsyncConnection:
    """Call once inside the outer business transaction, before its first SQL."""
    if not session.in_transaction():
        raise RuntimeError(
            "Start the business transaction before acquiring a connection"
        )
    started = monotonic()
    outcome = AcquisitionOutcome.FAILED
    try:
        connection = await session.connection()
        outcome = AcquisitionOutcome.ACQUIRED
        return connection
    except TimeoutError:
        outcome = AcquisitionOutcome.TIMEOUT
        raise
    finally:
        metrics.record_acquisition(outcome, monotonic() - started)
