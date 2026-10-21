import io
from pathlib import Path

import pytest
from conftest import read, write

from file_commentator import __version__
from file_commentator.cli import main

HEADER = ["--header", "Copyright {year} Example", "--var", "year=2026"]
EXPECTED = "# Copyright 2026 Example\n\nx = 1\n"


@pytest.fixture
def project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "src").mkdir()
    write(tmp_path / "src" / "a.py", "x = 1\n")
    write(tmp_path / "src" / "b.py", "x = 1\n")
    return tmp_path


def test_add_check_remove(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["check", *HEADER]) == 1
    out, err = capsys.readouterr()
    assert "missing" in out
    assert "2 files missing the header" in err

    assert main(["add", *HEADER]) == 0
    assert read(project / "src" / "a.py") == EXPECTED
    assert "Added the header to 2 files." in capsys.readouterr().err

    assert main(["check", *HEADER]) == 0
    assert "All files have the header (2 files checked)." in capsys.readouterr().err

    assert main(["remove", *HEADER]) == 0
    assert read(project / "src" / "a.py") == "x = 1\n"


def test_dry_run_lists_files_without_writing(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["add", *HEADER, "--dry-run"]) == 0

    out, err = capsys.readouterr()
    assert "would add" in out
    assert "Would add the header to 2 files." in err
    assert read(project / "src" / "a.py") == "x = 1\n"


def test_diff_prints_a_patch_without_writing(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["add", "src/a.py", *HEADER, "--diff"]) == 0

    out = capsys.readouterr().out
    assert out.startswith("--- a/src/a.py\n+++ b/src/a.py\n")
    assert "+# Copyright 2026 Example\n" in out
    assert read(project / "src" / "a.py") == "x = 1\n"


def test_quiet_prints_nothing_on_success(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["add", *HEADER, "-q"]) == 0

    assert capsys.readouterr() == ("", "")


def test_verbose_lists_skipped_files_with_reasons(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (project / "logo.png").write_bytes(b"\x89PNG")

    main(["add", *HEADER, "-v"])

    assert "skipped      logo.png (unsupported file type)" in capsys.readouterr().out


def test_update_refreshes_an_old_year(project: Path) -> None:
    path = project / "src" / "a.py"
    write(path, "# Copyright 2020 Example\n\nx = 1\n")

    assert main(["check", *HEADER]) == 1  # b.py is missing it; a.py is fine as it is
    main(["add", *HEADER])
    assert read(path) == "# Copyright 2020 Example\n\nx = 1\n"
    assert main(["check", *HEADER]) == 0
    assert main(["check", *HEADER, "--update"]) == 1

    main(["add", *HEADER, "--update"])
    assert read(path) == EXPECTED


def test_failed_file_gives_exit_code_1(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (project / "src" / "c.py").write_bytes(b"caf\xe9 = 1\n")

    assert main(["add", *HEADER]) == 1
    assert "error: " in capsys.readouterr().err


def test_include_exclude_and_style(project: Path) -> None:
    write(project / "notes.txt", "x = 1\n")
    write(project / "src" / "skip.py", "x = 1\n")

    main(
        ["add", *HEADER, "--include", "*.py,*.txt", "--exclude", "skip.py", "--style", "*.txt=hash"]
    )

    assert read(project / "notes.txt") == EXPECTED
    assert read(project / "src" / "skip.py") == "x = 1\n"


def test_header_file(project: Path) -> None:
    write(project / "HEADER.txt", "Copyright {year} Example\n")

    main(["add", "src", "--header-file", "HEADER.txt", "--var", "year=2026"])

    assert read(project / "src" / "a.py") == EXPECTED


def test_settings_from_commentator_toml(project: Path) -> None:
    write(project / "HEADER.txt", "Copyright {year} Example\n")
    (project / ".commentator.toml").write_text(
        'header-file = "HEADER.txt"\nexclude = ["b.py"]\n[variables]\nyear = "2026"\n'
    )

    assert main(["add"]) == 0

    assert read(project / "src" / "a.py") == EXPECTED
    assert read(project / "src" / "b.py") == "x = 1\n"


def test_settings_from_pyproject_in_a_parent_folder(
    project: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (project / "pyproject.toml").write_text(
        '[tool.commentator]\nheader = "Copyright {year} Example"\nvariables = { year = "2026" }\n'
    )
    monkeypatch.chdir(project / "src")

    assert main(["add"]) == 0
    assert read(project / "src" / "a.py") == EXPECTED


def test_command_line_overrides_settings(project: Path) -> None:
    write(project / ".commentator.toml", 'header = "From settings"\n')

    main(["add", "src/a.py", *HEADER])

    assert read(project / "src" / "a.py") == EXPECTED


@pytest.mark.parametrize(
    ("arguments", "settings", "message"),
    [
        (["add"], None, "no header given"),
        (["add", "missing-folder", *HEADER], None, "no such file or folder"),
        (["add", *HEADER, "--var", "year"], None, "--var expects NAME=VALUE"),
        (["add", *HEADER, "--style", "*.txt=pound"], None, "unknown comment style"),
        (["add", "--header", "{year}"], None, "fixed text"),
        (["add", "--header-file", "nope.txt"], None, "cannot read nope.txt"),
        (["add"], 'header = "x"\ncolour = "red"\n', "unknown setting 'colour'"),
        (["add"], 'header = "x"\ninclude = "*.py"\n', "'include' must be a list"),
        (["add"], "header = \n", "not valid TOML"),
    ],
)
def test_usage_errors(
    project: Path,
    capsys: pytest.CaptureFixture[str],
    arguments: list[str],
    settings: str | None,
    message: str,
) -> None:
    if settings is not None:
        write(project / ".commentator.toml", settings)

    assert main(arguments) == 2

    assert message in capsys.readouterr().err
    assert read(project / "src" / "a.py") == "x = 1\n"


def test_no_files_found(project: Path, capsys: pytest.CaptureFixture[str]) -> None:
    (project / "empty").mkdir()

    assert main(["add", "empty", *HEADER]) == 0
    assert "No files found." in capsys.readouterr().err


def test_styles_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["styles"]) == 0

    out = capsys.readouterr().out
    assert "hash        # ..." in out
    assert "Python" in out


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(["--version"])

    assert exit_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"commentator {__version__}"


def test_no_arguments_outside_a_terminal_prints_help(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("sys.stdin", io.StringIO())

    assert main([]) == 2
    assert "usage: commentator" in capsys.readouterr().err
