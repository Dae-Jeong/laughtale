"""Explicit local replication smoke. Creates then removes one uniquely named probe."""

import argparse
import asyncio
import json
import subprocess
import time
from pathlib import Path
from uuid import uuid4

import asyncpg
from chat_service.bootstrap.app import create_app
from chat_service.core.database import acquire_primary_connection, primary_session
from chat_service.core.settings import Settings
from dotenv import dotenv_values
from sqlalchemy import URL, text

ROOT = Path(__file__).resolve().parent
PROJECT = "laughtale-postgres-lab"
DB = "laughtale_chat"


def compose(*args: str) -> None:
    subprocess.run(
        [
            "docker",
            "compose",
            "--env-file",
            str(ROOT / ".env"),
            "-f",
            str(ROOT / "compose.yaml"),
            *args,
        ],
        check=True,
        timeout=60,
        capture_output=True,
    )


def admin(service: str, sql: str) -> str:
    result = subprocess.run(
        [
            "docker",
            "exec",
            "-i",
            f"{PROJECT}-{service}-1",
            "psql",
            "-U",
            "postgres",
            "-d",
            DB,
            "-X",
            "-At",
            "-v",
            "ON_ERROR_STOP=1",
        ],
        input=sql,
        text=True,
        capture_output=True,
        check=True,
        timeout=10,
    )
    return result.stdout.strip()


def verify_target(service: str, port: int) -> None:
    result = subprocess.run(
        [
            "docker",
            "inspect",
            "--format",
            '{{index .Config.Labels "com.docker.compose.project"}}|'
            '{{index .Config.Labels "com.docker.compose.service"}}|'
            "{{json .NetworkSettings.Ports}}",
            f"{PROJECT}-{service}-1",
        ],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    )
    project, actual_service, ports = result.stdout.strip().split("|", 2)
    assert project == PROJECT and actual_service == service
    assert json.loads(ports)["5432/tcp"] == [
        {"HostIp": "127.0.0.1", "HostPort": str(port)}
    ]


async def expected_error(connection, sql: str, sqlstate: str) -> None:
    try:
        await connection.execute(sql)
    except asyncpg.PostgresError as error:
        assert error.sqlstate == sqlstate, (error.sqlstate, sqlstate)
    else:
        raise AssertionError(f"Expected SQLSTATE {sqlstate}")


async def wait_rows(connection, table: str, count: int) -> None:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        try:
            if await connection.fetchval(f"SELECT count(*) FROM {table}") == count:
                return
        except asyncpg.UndefinedTableError:
            pass
        await asyncio.sleep(0.1)
    raise AssertionError("Replica did not catch up within smoke budget (20s)")


async def run(restart_replica: bool) -> None:
    verify_target("primary", 5440)
    verify_target("replica", 5441)
    assert admin("primary", "SELECT pg_is_in_recovery();") == "f"
    assert admin("replica", "SELECT pg_is_in_recovery();") == "t"
    assert admin(
        "primary", "SELECT system_identifier FROM pg_control_system();"
    ) == admin("replica", "SELECT system_identifier FROM pg_control_system();")
    secrets = dotenv_values(ROOT / ".env")

    async def connect(port: int, role: str):
        key = (
            "CHAT_WRITER_PASSWORD" if role == "chat_writer" else "CHAT_READER_PASSWORD"
        )
        password = secrets[key]
        assert password
        return await asyncpg.connect(
            host="127.0.0.1",
            port=port,
            database=DB,
            user=role,
            password=password,
            timeout=5,
            command_timeout=5,
        )

    writer = reader = replica = replica_writer = None
    table = "chat.replication_probe_" + uuid4().hex
    created = False
    try:
        writer = await connect(5440, "chat_writer")
        reader = await connect(5440, "chat_reader")
        replica = await connect(5441, "chat_reader")
        replica_writer = await connect(5441, "chat_writer")
        for connection in (writer, reader, replica_writer):
            assert await connection.fetchval(
                "SELECT NOT (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication) "
                "FROM pg_roles WHERE rolname=current_user"
            )
        admin(
            "primary",
            f"SET ROLE chat_owner; CREATE TABLE {table} (id integer PRIMARY KEY);",
        )
        created = True
        await writer.execute(f"INSERT INTO {table} VALUES (1)")
        await wait_rows(replica, table, 1)
        await expected_error(reader, f"INSERT INTO {table} VALUES (2)", "42501")
        await expected_error(
            writer, f"CREATE TABLE {table}_forbidden (id int)", "42501"
        )
        await expected_error(
            reader, f"CREATE TABLE {table}_forbidden (id int)", "42501"
        )
        # Using the writer credential proves standby protection, not merely reader ACLs.
        await expected_error(replica_writer, f"INSERT INTO {table} VALUES (2)", "25006")
        transaction = writer.transaction()
        await transaction.start()
        await writer.execute(f"INSERT INTO {table} VALUES (2)")
        await transaction.rollback()
        assert await reader.fetchval(f"SELECT count(*) FROM {table}") == 1

        if restart_replica:
            await replica.close()
            await replica_writer.close()
            try:
                compose("stop", "replica")
                await writer.execute(f"INSERT INTO {table} VALUES (3)")
                assert await reader.fetchval(f"SELECT count(*) FROM {table}") == 2
            finally:
                compose(
                    "up",
                    "-d",
                    "--no-deps",
                    "--no-recreate",
                    "--wait",
                    "--wait-timeout",
                    "45",
                    "replica",
                )
            replica = await connect(5441, "chat_reader")
            await wait_rows(replica, table, 2)

        streaming = admin(
            "primary",
            "SELECT state || ':' || sync_state FROM pg_stat_replication WHERE application_name='chat_replica';",
        )
        assert streaming == "streaming:async", streaming
        settings = Settings(
            _env_file=None,
            db_primary_url=URL.create(
                "postgresql+asyncpg",
                username="chat_writer",
                password=secrets["CHAT_WRITER_PASSWORD"],
                host="127.0.0.1",
                port=5440,
                database=DB,
            ).render_as_string(hide_password=False),
        )
        app = create_app(settings)
        async with app.router.lifespan_context(app):
            assert app.state.ready
            async with (
                primary_session(
                    app.state.primary_session_factory, app.state.database_metrics
                ) as session,
                session.begin(),
            ):
                await acquire_primary_connection(session, app.state.database_metrics)
                assert await session.scalar(text("SELECT current_database()")) == DB
                assert (
                    await session.scalar(text("SELECT current_user")) == "chat_writer"
                )
                assert await session.scalar(text("SELECT pg_is_in_recovery()")) is False
        assert app.state.ready is False
        assert not hasattr(app.state, "primary_engine")
        print(
            json.dumps(
                {
                    "primary": "read-write",
                    "replica": "read-only",
                    "replication": streaming,
                    "same_system_identifier": True,
                    "reader_write_and_ddl_denied": True,
                    "writer_ddl_denied": True,
                    "replica_writer_denied": True,
                    "rollback_verified": True,
                    "replica_restart_catchup": restart_replica,
                    "chat_app_primary_lifespan": True,
                }
            )
        )
    finally:
        for connection in (writer, reader, replica, replica_writer):
            if connection is not None and not connection.is_closed():
                await connection.close()
        if created:
            admin("primary", f"SET ROLE chat_owner; DROP TABLE {table};")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--restart-replica", action="store_true")
    args = parser.parse_args()
    try:
        asyncio.run(run(args.restart_replica))
    except Exception as error:
        # Never print driver errors containing connection strings or credentials.
        raise SystemExit(f"Replication smoke failed: {type(error).__name__}") from None
