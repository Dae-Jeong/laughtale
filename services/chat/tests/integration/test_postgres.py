import asyncio
import os
import subprocess
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import monotonic
from uuid import uuid4

import asyncpg
import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError, TimeoutError
from tests.postgres_support import validate_test_url

from chat_service.bootstrap.app import create_app
from chat_service.contracts.database import TransactionOutcome
from chat_service.core.database import acquire_primary_connection, primary_session
from chat_service.core.settings import Settings

pytestmark = pytest.mark.postgres


@asynccontextmanager
async def database(url: str, **overrides) -> AsyncIterator:
    validate_test_url(url)
    app = create_app(Settings(db_primary_url=url, **overrides))
    schema = "run_" + uuid4().hex
    async with app.router.lifespan_context(app):
        engine = app.state.primary_engine
        async with engine.begin() as connection:
            identity = (
                await connection.execute(
                    text("SELECT current_database(),current_user,pg_is_in_recovery()")
                )
            ).one()
            if tuple(identity) != ("laughtale_chat_test", "chat_test", False):
                raise RuntimeError("Unexpected connected test target")
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
            await connection.execute(
                text(f"CREATE TABLE {schema}.parent (id int PRIMARY KEY)")
            )
            await connection.execute(
                text(
                    f"CREATE TABLE {schema}.child (id int REFERENCES {schema}.parent(id) DEFERRABLE INITIALLY DEFERRED)"
                )
            )
        try:
            yield app, schema
        finally:
            async with engine.begin() as connection:
                await connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    assert not app.state.ready
    assert not hasattr(app.state, "primary_engine")


def metric(app, name: str, **labels: str):
    return app.state.metrics.registry.get_sample_value(
        name, {"role": "primary", **labels}
    )


async def write_sample(session, metrics, schema: str, mode: str, entered=None) -> None:
    """Synthetic business boundary, not a chat implementation."""
    started = monotonic()
    body_error = None
    outcome = TransactionOutcome.FAILED
    try:
        async with session.begin():
            try:
                await acquire_primary_connection(session, metrics)
                await session.execute(text(f"INSERT INTO {schema}.parent VALUES (1)"))
                await session.execute(
                    text(f"INSERT INTO {schema}.child VALUES (:id)"),
                    {"id": 2 if mode == "commit_failure" else 1},
                )
                if mode == "body_failure":
                    raise ValueError("synthetic business failure")
                if mode == "cancel":
                    if entered is None:
                        raise ValueError("Cancellation test requires a signal")
                    entered.set()
                    await asyncio.Future()
            except BaseException as error:
                body_error = error
                raise
        outcome = TransactionOutcome.COMMITTED
    except BaseException as error:
        if error is body_error:
            outcome = TransactionOutcome.ROLLED_BACK
        raise
    finally:
        metrics.record_transaction(outcome, monotonic() - started)


@pytest.mark.parametrize(
    "mode", ["success", "body_failure", "commit_failure", "cancel"]
)
def test_atomicity_and_metrics(postgres_url: str, mode: str) -> None:
    async def scenario():
        async with database(postgres_url) as (app, schema):
            metrics = app.state.database_metrics
            entered = asyncio.Event()

            async def work():
                async with primary_session(
                    app.state.primary_session_factory, metrics
                ) as session:
                    await write_sample(session, metrics, schema, mode, entered)

            if mode == "cancel":
                task = asyncio.create_task(work())
                try:
                    await asyncio.wait_for(entered.wait(), 5)
                finally:
                    task.cancel()
                    with pytest.raises(asyncio.CancelledError):
                        await task
            elif mode == "success":
                await work()
            else:
                with pytest.raises(
                    ValueError if mode == "body_failure" else IntegrityError
                ):
                    await work()
            async with app.state.primary_engine.connect() as connection:
                for table in ("parent", "child"):
                    assert await connection.scalar(
                        text(f"SELECT count(*) FROM {schema}.{table}")
                    ) == (1 if mode == "success" else 0)
            outcome = {
                "success": "committed",
                "body_failure": "rolled_back",
                "cancel": "rolled_back",
                "commit_failure": "failed",
            }[mode]
            assert metric(app, "db_transactions_total", outcome=outcome) == 1
            if mode != "success":
                assert metric(app, "db_transactions_total", outcome="committed") == 0
            assert metric(app, "db_sessions_active") == 0
            assert metric(app, "db_pool_connections_in_use") == 0

    asyncio.run(scenario())


def test_pool_timeout_and_reuse(postgres_url: str) -> None:
    async def scenario():
        async with database(
            postgres_url, db_pool_size=1, db_pool_timeout_seconds=0.05
        ) as (app, _):
            factory, metrics = (
                app.state.primary_session_factory,
                app.state.database_metrics,
            )
            async with primary_session(factory, metrics) as first, first.begin():
                await acquire_primary_connection(first, metrics)
                async with primary_session(factory, metrics) as second:
                    with pytest.raises(TimeoutError):
                        async with second.begin():
                            await acquire_primary_connection(second, metrics)
            assert metric(app, "db_pool_timeouts_total") == 1
            async with primary_session(factory, metrics) as session, session.begin():
                await acquire_primary_connection(session, metrics)
                assert await session.scalar(text("SELECT 1")) == 1
            assert metric(app, "db_sessions_active") == 0
            assert metric(app, "db_pool_connections_in_use") == 0

    asyncio.run(scenario())


@pytest.mark.parametrize(
    "mode,sqlstate", [("lock", "55P03"), ("statement", "57014"), ("cancel_query", None)]
)
def test_server_timeout_and_query_cancellation(
    postgres_url: str, mode: str, sqlstate: str | None
) -> None:
    async def scenario():
        async with database(
            postgres_url,
            db_lock_timeout_ms=50,
            db_statement_timeout_ms=150 if mode == "statement" else 5000,
        ) as (app, schema):
            factory, metrics = (
                app.state.primary_session_factory,
                app.state.database_metrics,
            )
            async with app.state.primary_engine.begin() as conn:
                await conn.execute(text(f"INSERT INTO {schema}.parent VALUES (1)"))
            async with primary_session(factory, metrics) as blocker, blocker.begin():
                await blocker.execute(
                    text(f"UPDATE {schema}.parent SET id=1 WHERE id=1")
                )
                entered = asyncio.Event()
                backend_pid = []

                async def query():
                    async with (
                        primary_session(factory, metrics) as session,
                        session.begin(),
                    ):
                        await acquire_primary_connection(session, metrics)
                        backend_pid.append(
                            await session.scalar(text("SELECT pg_backend_pid()"))
                        )
                        entered.set()
                        await session.execute(
                            text(
                                f"UPDATE {schema}.parent SET id=2 WHERE id=1"
                                if mode == "lock"
                                else "SELECT pg_sleep(5)"
                            )
                        )

                if mode == "cancel_query":
                    task = asyncio.create_task(query())
                    try:
                        await asyncio.wait_for(entered.wait(), 5)
                        deadline = monotonic() + 3
                        while monotonic() < deadline:
                            async with app.state.primary_engine.connect() as observer:
                                event = await observer.scalar(
                                    text(
                                        "SELECT wait_event FROM pg_stat_activity WHERE pid=:pid"
                                    ),
                                    {"pid": backend_pid[0]},
                                )
                            if event == "PgSleep":
                                break
                            await asyncio.sleep(0.01)
                        else:
                            raise AssertionError("Query never reached PostgreSQL sleep")
                    finally:
                        task.cancel()
                        with pytest.raises(asyncio.CancelledError):
                            await task
                else:
                    with pytest.raises(DBAPIError) as error:
                        await query()
                    assert getattr(error.value.orig, "sqlstate", None) == sqlstate
            assert metric(app, "db_pool_timeouts_total") == 0
            async with primary_session(factory, metrics) as session, session.begin():
                await acquire_primary_connection(session, metrics)
                assert (
                    await session.scalar(text(f"SELECT id FROM {schema}.parent")) == 1
                )
            assert metric(app, "db_sessions_active") == 0
            assert metric(app, "db_pool_connections_in_use") == 0

    asyncio.run(scenario())


def test_test_role_cannot_connect_to_development_database(postgres_url: str) -> None:
    async def scenario():
        url = validate_test_url(postgres_url)
        with pytest.raises(asyncpg.PostgresError):
            await asyncpg.connect(
                host=url.host,
                port=url.port,
                user=url.username,
                password=url.password,
                database="laughtale_chat",
                timeout=2,
            )

    asyncio.run(scenario())


def test_bad_credentials_startup_does_not_leak_secret(
    postgres_url: str, tmp_path
) -> None:
    marker = "synthetic-startup-secret"
    url = validate_test_url(postgres_url).set(password=marker)
    result = subprocess.run(
        [sys.executable, "-m", "chat_service.run"],
        cwd=tmp_path,
        env={
            **os.environ,
            "DB_PRIMARY_URL": url.render_as_string(hide_password=False),
            "DB_CONNECT_TIMEOUT_SECONDS": "1",
        },
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert marker not in result.stdout + result.stderr
    assert "server.listening" not in result.stdout


@pytest.mark.parametrize("mode", ["bad_password", "unavailable"])
def test_startup_failure_disposes_engine(
    postgres_url: str, mode: str, monkeypatch
) -> None:
    import socket

    from chat_service.bootstrap import lifespan

    async def scenario():
        url = validate_test_url(postgres_url)
        disposed = []
        original = lifespan.create_primary_engine

        def capture(settings, metrics):
            engine = original(settings, metrics)
            dispose = engine.dispose

            # Observe disposal while retaining the real connection implementation.
            class TrackedEngine:
                def connect(self):
                    return engine.connect()

                async def dispose(self):
                    await dispose()
                    disposed.append(True)

            return TrackedEngine()

        monkeypatch.setattr(lifespan, "create_primary_engine", capture)
        # Bound but not listening: guarantees a local unused endpoint, without stopping a DB.
        with socket.socket() as closed_endpoint:
            closed_endpoint.bind(("127.0.0.1", 0))
            target = (
                url.set(password="synthetic-bad-password")
                if mode == "bad_password"
                else url.set(
                    port=closed_endpoint.getsockname()[1],
                    password="synthetic-unused-password",
                )
            )
            app = create_app(
                Settings(
                    db_primary_url=target.render_as_string(hide_password=False),
                    db_connect_timeout_seconds=1,
                )
            )
            started = monotonic()
            with pytest.raises(
                asyncpg.InvalidPasswordError
                if mode == "bad_password"
                else (ConnectionRefusedError, asyncio.TimeoutError)
            ):
                async with app.router.lifespan_context(app):
                    pytest.fail("Unexpected successful startup")
            assert monotonic() - started < 5
        assert disposed == [True]
        assert app.state.ready is False
        assert not hasattr(app.state, "primary_engine")
        assert metric(app, "db_pool_connections_in_use") == 0

    asyncio.run(scenario())
