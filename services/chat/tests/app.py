"""Template HTTP regression fixtures; never registered by the service runtime."""

from typing import Annotated

from fastapi import FastAPI, Query
from pydantic import StringConstraints

from chat_service.bootstrap.app import create_app as create_service_app
from chat_service.bootstrap.contracts import PrepareResources
from chat_service.core.clock import system_clock
from chat_service.core.contracts import Clock
from chat_service.core.settings import Settings
from chat_service.http.errors import PROBLEM_RESPONSES
from chat_service.schemas.responses import MessageData, Success


def create_app(
    settings: Settings,
    *,
    clock: Clock = system_clock,
    prepare: PrepareResources | None = None,
) -> FastAPI:
    app = create_service_app(settings, clock=clock, prepare=prepare)

    @app.get("/v1/greetings", responses=PROBLEM_RESPONSES)
    def greet(
        name: Annotated[
            str,
            StringConstraints(strip_whitespace=True, min_length=1, max_length=80),
            Query(),
        ],
    ) -> Success[MessageData]:
        return Success(data=MessageData(message=f"Hello, {name}!"))

    return app
