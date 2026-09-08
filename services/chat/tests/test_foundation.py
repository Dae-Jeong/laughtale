import asyncio

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from chat_service.bootstrap.app import create_app
from chat_service.core.database import create_primary_engine
from chat_service.core.database_metrics import create_database_metrics
from chat_service.core.metrics import create_metrics
from chat_service.core.settings import Settings


def test_runtime_has_no_template_business_routes() -> None:
    app = create_app(Settings())
    with TestClient(app) as client:
        assert client.get("/").json() == {"data": {"message": "Chat service"}}
        assert client.get("/health/ready").status_code == 200
        assert client.get("/metrics").status_code == 200
        paths = client.get("/openapi.json").json()["paths"]
        assert "/v1/greetings" not in paths
        assert "/v1/reservations" not in paths
        assert client.get("/v1/greetings").status_code == 404
    assert app.state.ready is False


def test_postgresql_engine_configuration_without_connecting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from chat_service.core import database

    settings = Settings(
        db_primary_url="postgresql+asyncpg://user:synthetic-secret@127.0.0.1:5434/laughtale_chat"
    )
    assert "synthetic-secret" not in repr(settings)
    actual = database.create_async_engine
    captured = {}

    def capture(url, **kwargs):
        captured.update(kwargs)
        return actual(url, **kwargs)

    monkeypatch.setattr(database, "create_async_engine", capture)
    engine = create_primary_engine(
        settings, create_database_metrics(create_metrics(), 4)
    )
    try:
        assert engine.dialect.name == "postgresql"
        assert engine.dialect.driver == "asyncpg"
        assert captured["connect_args"] == {
            "timeout": 3,
            "server_settings": {
                "application_name": "Laughtale Chat",
                "statement_timeout": "5000",
                "lock_timeout": "1000",
            },
        }
        assert captured["hide_parameters"] is True
        assert captured["pool_pre_ping"] is True
    finally:
        asyncio.run(engine.dispose())


@pytest.mark.parametrize(
    "url",
    [
        "sqlite+aiosqlite:///data.db",
        "postgresql+asyncpg:///missing-host",
        "postgresql+asyncpg://localhost/",
        "postgresql+asyncpg://localhost/db?statement_timeout=0",
    ],
)
def test_postgresql_configuration_rejects_unsupported_urls(url: str) -> None:
    with pytest.raises(ValidationError):
        Settings(db_primary_url=url)
