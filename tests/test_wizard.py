from collections.abc import Iterator
from pathlib import Path

import pytest
from conftest import read, write

from file_commentator import wizard


def answer(monkeypatch: pytest.MonkeyPatch, *replies: str) -> None:
    """Feed replies to input(), and fail if the wizard asks for more."""
    queue: Iterator[str] = iter(replies)

    def fake_input(prompt: str = "") -> str:
        try:
            return next(queue)
        except StopIteration:
            raise AssertionError(f"unexpected question: {prompt!r}") from None

    monkeypatch.setattr("builtins.input", fake_input)


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    write(tmp_path / "a.py", "x = 1\n")
    write(tmp_path / "b.js", "let x = 1;\n")
    return tmp_path


def test_typed_header_is_added_after_confirmation(
    project: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    answer(monkeypatch, "", "", "Made by Example", "", "Second line", ".", "*.py", "y")

    assert wizard.run_wizard() == 0

    assert read(project / "a.py") == "# Made by Example\n#\n# Second line\n\nx = 1\n"
    assert read(project / "b.js") == "let x = 1;\n"
    out = capsys.readouterr().out
    assert "+# Made by Example" in out
    assert "Added the header to 1 file." in out


def test_header_from_a_file_with_quoted_paths(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write(project / "HEADER.txt", "From a file\n")
    answer(monkeypatch, f'"{project}"', '"HEADER.txt"', "", "yes")

    assert wizard.run_wizard() == 0

    assert read(project / "a.py") == "# From a file\n\nx = 1\n"
    assert read(project / "b.js").startswith("/*\n * From a file\n */\n")


def test_bad_answers_are_asked_again(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    answer(monkeypatch, "no-such-folder", ".", "missing.txt", "", ".", "", "OK", ".", "", "n")

    assert wizard.run_wizard() == 0

    assert read(project / "a.py") == "x = 1\n"


def test_declining_changes_nothing(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    answer(monkeypatch, "", "", "Header", ".", "", "")

    assert wizard.run_wizard() == 0
    assert read(project / "a.py") == "x = 1\n"


def test_ctrl_c_cancels(project: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def interrupt(prompt: str = "") -> str:
        raise KeyboardInterrupt

    monkeypatch.setattr("builtins.input", interrupt)

    assert wizard.run_wizard() == 130
    assert read(project / "a.py") == "x = 1\n"
