from pathlib import Path

import pytest

from file_commentator.header import Header
from file_commentator.languages import Language, builtin_language

HEADER_TEXT = "Copyright {year} Example Corp\nSPDX-License-Identifier: MIT"


def write(path: Path, text: str) -> None:
    """Write text exactly as given (Path.write_text changes line endings on Windows)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode())


def read(path: Path) -> str:
    """Read text exactly, without converting line endings."""
    return path.read_bytes().decode()


def language(filename: str) -> Language:
    """The built-in language for a file name; fails the test if there is none."""
    found = builtin_language(filename)
    assert found is not None, filename
    return found


@pytest.fixture
def header() -> Header:
    return Header(HEADER_TEXT, {"year": "2026"})
