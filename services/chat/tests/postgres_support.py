from sqlalchemy.engine import URL, make_url


def validate_test_url(value: str) -> URL:
    """Safety gate: must run before opening a connection or executing DDL."""
    try:
        url = make_url(value)
    except Exception:
        raise ValueError("Invalid test database URL") from None
    if (
        url.drivername != "postgresql+asyncpg"
        or url.host != "127.0.0.1"
        or url.port != 5440
        or url.database != "laughtale_chat_test"
        or url.username != "chat_test"
        or not url.password
        or url.query
    ):
        raise ValueError("Only the isolated lab test database is allowed")
    return url
