import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

from file_commentator.files import Selection, find_files, write_atomic


def make(root: Path, *names: str) -> None:
    for name in names:
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x\n")


def found(root: Path, selection: Selection | None = None, *, gitignore: bool = True) -> list[str]:
    result = find_files([root], selection or Selection(), gitignore=gitignore)
    return sorted(path.relative_to(root).as_posix() for path in result.files)


@pytest.fixture
def cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_skips_tool_and_build_folders_but_not_files_with_those_names(cwd: Path) -> None:
    make(cwd, "src/a.py", "node_modules/x/b.js", ".venv/lib/c.py", "src/build/d.py", "build")

    assert found(cwd) == ["build", "src/a.py"]


def test_include_and_exclude_patterns(cwd: Path) -> None:
    make(cwd, "src/a.py", "src/b.js", "src/gen/c.py", "tests/fixtures/d.py", "tests/e.py")
    selection = Selection(include=("*.py",), exclude=("gen", "tests/fixtures"))

    assert found(cwd, selection) == ["src/a.py", "tests/e.py"]


def test_patterns_with_a_slash_match_paths_from_the_current_folder(cwd: Path) -> None:
    make(cwd, "src/a.py", "src/sub/b.py", "lib/c.py")

    assert found(cwd, Selection(include=("src/*",))) == ["src/a.py", "src/sub/b.py"]
    # Running on a subfolder does not change what the pattern refers to.
    result = find_files([cwd / "src"], Selection(exclude=("src/sub",)))
    assert [p.name for p in result.files] == ["a.py"]


def test_explicit_files_are_checked_against_patterns(cwd: Path) -> None:
    make(cwd, "a.py", "vendor/b.py")
    files = [Path("a.py"), Path("vendor/b.py")]

    result = find_files(files, Selection(exclude=("vendor",)))

    assert result.files == [Path("a.py")]


def test_overlapping_paths_are_listed_once(cwd: Path) -> None:
    make(cwd, "src/a.py")

    result = find_files([cwd, cwd / "src", Path("src/a.py")], Selection())

    assert len(result.files) == 1


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_respects_gitignore_in_a_repository(cwd: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=cwd, check=True)
    make(
        cwd,
        ".gitignore",
        "tracked.py",
        "build/tracked_build.py",
        "new.py",
        "ignored/x.py",
        ".venv/lib.py",
    )
    (cwd / ".gitignore").write_text("ignored/\n")
    subprocess.run(["git", "add", "tracked.py", "build", ".gitignore"], cwd=cwd, check=True)

    assert found(cwd) == [".gitignore", "build/tracked_build.py", "new.py", "tracked.py"]
    assert "ignored/x.py" in found(cwd, gitignore=False)


def test_write_atomic_replaces_contents_and_leaves_no_temporary_file(tmp_path: Path) -> None:
    path = tmp_path / "a.txt"
    path.write_bytes(b"old")

    write_atomic(path, b"new contents")

    assert path.read_bytes() == b"new contents"
    assert os.listdir(tmp_path) == ["a.txt"]


@pytest.mark.skipif(os.name == "nt", reason="POSIX permissions")
def test_write_atomic_keeps_permissions(tmp_path: Path) -> None:
    path = tmp_path / "script.sh"
    path.write_text("echo\n")
    path.chmod(0o751)

    write_atomic(path, b"echo hi\n")

    assert stat.S_IMODE(path.stat().st_mode) == 0o751
