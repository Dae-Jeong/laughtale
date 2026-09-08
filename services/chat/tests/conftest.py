import os
from pathlib import Path

import pytest

from chat_service.core import logging as service_logging
from chat_service.core.settings import Settings
from chat_service.http import errors
from tests.postgres_support import validate_test_url


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--postgres", action="store_true", help="Run real PostgreSQL tests"
    )


def pytest_configure(config: pytest.Config) -> None:
    if config.getoption("--postgres"):
        try:
            validate_test_url(os.environ.get("CHAT_TEST_DATABASE_URL", ""))
        except ValueError as error:
            raise pytest.UsageError(str(error)) from None


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    if not config.getoption("--postgres"):
        selected = [item for item in items if not item.get_closest_marker("postgres")]
        config.hook.pytest_deselected(
            items=[item for item in items if item not in selected]
        )
        items[:] = selected


@pytest.fixture
def postgres_url() -> str:
    value = os.environ.get("CHAT_TEST_DATABASE_URL", "")
    validate_test_url(value)
    return value


@pytest.fixture(autouse=True)
def isolate_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    for name in tuple(os.environ):
        if name.lower() in Settings.model_fields:
            monkeypatch.delenv(name)
    # Only the synthetic test route exposes this field location.
    monkeypatch.setattr(errors, "PUBLIC_LOCATIONS", {("query", "name")})
    monkeypatch.setattr(
        service_logging, "EVENTS", service_logging.EVENTS | {"greeting.completed"}
    )
