from functools import partial

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from chat_service.bootstrap.contracts import PrepareResources
from chat_service.bootstrap.lifespan import (
    create_lifespan,
    prepare_resources,
)
from chat_service.core.clock import system_clock
from chat_service.core.contracts import Clock, LogContext
from chat_service.core.database_metrics import create_database_metrics
from chat_service.core.metrics import create_metrics
from chat_service.core.settings import Settings
from chat_service.exceptions.database import DatabaseBusy, DatabasePoolTimeout
from chat_service.http.database import database_unavailable
from chat_service.http.errors import (
    http_error,
    internal_error,
    problem_openapi,
    validation_error,
)
from chat_service.routers.health import router as health_router
from chat_service.routers.index import router as index_router
from chat_service.routers.metrics import router as metrics_router


def create_app(
    settings: Settings,
    *,
    clock: Clock = system_clock,
    prepare: PrepareResources | None = None,
) -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.service_version,
        lifespan=create_lifespan(
            prepare
            if prepare is not None
            else partial(prepare_resources, settings=settings)
        ),
    )
    app.state.clock = clock
    app.state.ready = False
    app.state.metrics = create_metrics()
    if settings.db_primary_url:
        app.state.database_metrics = create_database_metrics(
            app.state.metrics, settings.db_pool_size + settings.db_pool_max_overflow
        )
    app.state.log_context = LogContext(
        settings.app_name, settings.service_version, settings.app_environment
    )
    app.add_exception_handler(RequestValidationError, validation_error)
    app.add_exception_handler(HTTPException, http_error)
    app.add_exception_handler(Exception, internal_error)
    app.include_router(index_router)
    app.include_router(health_router)
    app.include_router(metrics_router)
    if settings.db_primary_url:
        app.add_exception_handler(DatabaseBusy, database_unavailable)
        app.add_exception_handler(DatabasePoolTimeout, database_unavailable)
    # FastAPI가 지원하는 인스턴스별 OpenAPI 함수 교체입니다. self는 partial로 고정합니다.
    app.openapi = partial(problem_openapi, app, app.openapi)  # ty: ignore[invalid-assignment]
    return app
