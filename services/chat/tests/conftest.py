import os
from pathlib import Path

import pytest

from chat_service.core import logging as service_logging
from chat_service.core.settings import Settings
from chat_service.http import errors


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
