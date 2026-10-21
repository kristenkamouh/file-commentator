"""Finding the files to process, and writing files safely."""

import itertools
import os
import shutil
import subprocess
import tempfile
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from fnmatch import fnmatch
from pathlib import Path, PurePosixPath

# Folders skipped unless git tracks files in them: version control, caches, and build output.
# fmt: off
DEFAULT_EXCLUDES = (
    ".git", ".hg", ".svn", "node_modules", "__pycache__", ".venv", "venv", ".tox", ".nox",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".idea", ".vscode", "dist", "build",
    "target", "*.egg-info",
)
# fmt: on


@dataclass(frozen=True)
class Selection:
    """Glob patterns that choose which files to process.

    A pattern without a slash matches a file or folder name anywhere. A pattern with a
    slash matches a path relative to the current folder, and ``*`` also matches slashes.
    """

    include: tuple[str, ...] = ()
    exclude: tuple[str, ...] = ()

    def wants_file(self, path: PurePosixPath) -> bool:
        """Check a file against the patterns. Its folders are checked separately."""
        if any(_matches(path, pattern) for pattern in self.exclude):
            return False
        return not self.include or any(_matches(path, pattern) for pattern in self.include)


@dataclass
class Discovery:
    """The files found, and any folders that could not be read."""

    files: list[Path] = field(default_factory=list)
    errors: list[tuple[Path, str]] = field(default_factory=list)
    used_git: bool = False


def find_files(paths: Sequence[Path], selection: Selection, *, gitignore: bool = True) -> Discovery:
    """Expand files and folders into a sorted list of files to process.

    Inside a git repository, folders are listed with git, so .gitignore is respected.
    Files given directly are only checked against the selection patterns.
    """
    found = Discovery()
    unique: dict[str, Path] = {}
    for root in paths:
        base = _relative_to_cwd(root)
        if root.is_dir():
            listed = _git_files(root) if gitignore else None
            if listed is None:
                names: Iterable[PurePosixPath] = _walk(root, base, selection, found.errors)
            else:
                found.used_git = True
                tracked, untracked = listed
                names = itertools.chain(
                    _filter(tracked, base, selection, selection.exclude),
                    _filter(untracked, base, selection, selection.exclude + DEFAULT_EXCLUDES),
                )
            for name in names:
                path = root / name
                unique.setdefault(os.path.normcase(os.path.abspath(path)), path)
        elif selection.wants_file(base) and not any(
            _matches(folder, pattern) for folder in base.parents for pattern in selection.exclude
        ):
            unique.setdefault(os.path.normcase(os.path.abspath(root)), root)
    found.files = sorted(unique.values())
    return found


def split_patterns(values: Iterable[str]) -> list[str]:
    """Flatten option values that may be repeated and comma-separated."""
    return [item.strip() for value in values for item in value.split(",") if item.strip()]


def display_path(path: Path) -> str:
    """Show a path relative to the current folder when it is inside it."""
    if path.is_absolute():
        try:
            return str(path.relative_to(Path.cwd()))
        except ValueError:
            pass
    return str(path)


def write_atomic(path: Path, data: bytes) -> None:
    """Replace a file's contents so that it is never left half-written.

    The data goes to a temporary file next to it, which then replaces the original.
    The original file's permissions, such as the executable bit, are kept.
    """
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
        if os.name != "nt":  # on Windows the mode only holds the read-only flag
            shutil.copymode(path, temporary)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def _matches(path: PurePosixPath, pattern: str) -> bool:
    pattern = pattern.removeprefix("./").strip("/")
    return fnmatch(path.as_posix() if "/" in pattern else path.name, pattern)


def _relative_to_cwd(path: Path) -> PurePosixPath:
    try:
        return PurePosixPath(Path(os.path.relpath(path)).as_posix())
    except ValueError:  # on another drive on Windows
        return PurePosixPath()


def _walk(
    root: Path, base: PurePosixPath, selection: Selection, errors: list[tuple[Path, str]]
) -> Iterator[PurePosixPath]:
    """List files under ``root``, skipping excluded folders without entering them."""
    folder_patterns = selection.exclude + DEFAULT_EXCLUDES

    def on_error(error: OSError) -> None:
        errors.append((Path(error.filename or root), error.strerror or str(error)))

    for current, folders, files in os.walk(root, onerror=on_error):
        folder = PurePosixPath(Path(os.path.relpath(current, root)).as_posix())
        folders[:] = [
            name
            for name in folders
            if not any(_matches(base / folder / name, pattern) for pattern in folder_patterns)
        ]
        for name in files:
            if selection.wants_file(base / folder / name):
                yield folder / name


def _filter(
    names: Iterable[str],
    base: PurePosixPath,
    selection: Selection,
    folder_patterns: Sequence[str],
) -> Iterator[PurePosixPath]:
    """Apply the patterns to a flat list of paths, such as the output of git."""
    excluded: dict[PurePosixPath, bool] = {}

    def is_excluded(folder: PurePosixPath) -> bool:
        if not folder.parts:
            return False
        if folder not in excluded:
            excluded[folder] = is_excluded(folder.parent) or any(
                _matches(base / folder, pattern) for pattern in folder_patterns
            )
        return excluded[folder]

    for name in names:
        path = PurePosixPath(name)
        if not is_excluded(path.parent) and selection.wants_file(base / path):
            yield path


def _git_files(root: Path) -> tuple[list[str], list[str]] | None:
    """List the files git tracks under ``root``, and the untracked ones it does not ignore.

    Returns None when ``root`` is not in a git repository or git is not installed.
    """
    tracked = _git_ls_files(root, "--cached")
    if tracked is None:
        return None
    return tracked, _git_ls_files(root, "--others", "--exclude-standard") or []


def _git_ls_files(root: Path, *options: str) -> list[str] | None:
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z", *options], cwd=root, capture_output=True, check=False
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return [name for name in result.stdout.decode("utf-8", "surrogateescape").split("\0") if name]
