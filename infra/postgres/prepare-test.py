"""Provision only a new isolated lab test DB; refuse existing names."""

import subprocess
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy.engine import make_url
from verify import admin, verify_target


def main() -> None:
    verify_target("primary", 5440)
    if admin("primary", "SELECT pg_is_in_recovery();") != "f":
        raise RuntimeError("Expected lab Primary")
    values = dotenv_values(
        Path(__file__).resolve().parents[2] / "services/chat/.env.test"
    )
    url = make_url(values.get("CHAT_TEST_DATABASE_URL") or "")
    if (
        (url.drivername, url.host, url.port, url.database, url.username)
        != ("postgresql+asyncpg", "127.0.0.1", 5440, "laughtale_chat_test", "chat_test")
        or not url.password
        or url.query
    ):
        raise ValueError("Unexpected test target")
    existing = admin(
        "primary",
        "SELECT datname FROM pg_database WHERE datname='laughtale_chat_test' UNION ALL SELECT rolname FROM pg_roles WHERE rolname='chat_test';",
    )
    if existing:
        raise RuntimeError("Test DB or role already exists; no changes made")
    password = url.password.replace("'", "''")
    sql = f"""
CREATE ROLE chat_test LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION PASSWORD '{password}';
CREATE DATABASE laughtale_chat_test;
REVOKE ALL ON DATABASE laughtale_chat_test FROM PUBLIC;
GRANT CONNECT, CREATE ON DATABASE laughtale_chat_test TO chat_test;
\\connect laughtale_chat_test
REVOKE ALL ON SCHEMA public FROM PUBLIC;
SELECT pg_reload_conf();
"""
    subprocess.run(
        [
            "docker",
            "exec",
            "-i",
            "laughtale-postgres-lab-primary-1",
            "psql",
            "-U",
            "postgres",
            "-d",
            "postgres",
            "-X",
            "-v",
            "ON_ERROR_STOP=1",
        ],
        input=sql,
        text=True,
        capture_output=True,
        check=True,
        timeout=15,
    )
    print("Created isolated test DB and non-superuser role; reloaded lab HBA")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # noqa: BLE001 -- CLI boundary must redact driver credentials.
        raise SystemExit(
            f"Test DB preparation failed: {type(error).__name__}"
        ) from None
