import subprocess
import sys

import pytest

from tests.postgres_support import validate_test_url


@pytest.mark.parametrize(
    "url",
    [
        "",
        "invalid",
        "postgresql+asyncpg://chat_test:secret@127.0.0.1:5433/laughtale_chat_test",
        "postgresql+asyncpg://chat_test:secret@127.0.0.1:5441/laughtale_chat_test",
        "postgresql+asyncpg://chat_test:secret@127.0.0.1:5440/laughtale_chat",
        "postgresql+asyncpg://postgres:secret@127.0.0.1:5440/laughtale_chat_test",
        "postgresql+asyncpg://chat_test:secret@remote:5440/laughtale_chat_test",
        "postgresql+asyncpg://chat_test:secret@127.0.0.1:5440/laughtale_chat_test?host=remote",
    ],
)
def test_wrong_database_rejected_before_connection(url: str) -> None:
    with pytest.raises(ValueError):
        validate_test_url(url)


def test_target_guard_is_not_removed_by_optimization() -> None:
    from pathlib import Path

    support = Path(__file__).with_name("postgres_support.py")
    result = subprocess.run(
        [
            sys.executable,
            "-O",
            "-c",
            "import runpy,sys; f=runpy.run_path(sys.argv[1])['validate_test_url']; f('invalid')",
            str(support),
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode != 0
    assert "Invalid test database URL" in result.stderr
