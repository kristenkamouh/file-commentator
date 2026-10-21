"""Applying a header change to each file, on a pool of threads."""

import codecs
import difflib
import stat
from collections import deque
from collections.abc import Callable, Iterator, Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from file_commentator.files import display_path, write_atomic
from file_commentator.header import Header, Status
from file_commentator.languages import FileTypes, language_from_shebang
from file_commentator.preamble import PlacementError

MAX_FILE_SIZE = 10 * 1024 * 1024
_SNIFF_SIZE = 8192  # bytes checked for a #! line and for binary content
_IN_FLIGHT = 256  # files queued on the pool at once


@dataclass(frozen=True)
class Job:
    """What to do to each file."""

    header: Header
    types: FileTypes
    remove: bool = False  # remove the header instead of adding it
    update: bool = False  # also rewrite headers whose placeholder values differ
    write: bool = True  # when False, only work out what would change
    diff: bool = False  # include a unified diff in each result


@dataclass(frozen=True)
class Result:
    """The outcome for one file."""

    path: Path
    status: Status
    detail: str = ""
    diff: str = ""


def run(
    files: Sequence[Path], job: Job, on_progress: Callable[[int, int], None] | None = None
) -> list[Result]:
    """Process files in parallel. Results come back in the same order as ``files``."""
    results: list[Result] = []
    executor = ThreadPoolExecutor()
    try:
        remaining = iter(files)
        queue: deque[Future[Result]] = deque(
            executor.submit(process_file, path, job) for path in _take(remaining, _IN_FLIGHT)
        )
        while queue:
            results.append(_wait(queue.popleft()))
            for path in _take(remaining, 1):
                queue.append(executor.submit(process_file, path, job))
            if on_progress is not None:
                on_progress(len(results), len(files))
    finally:
        # On Ctrl+C, queued files are dropped and files being written finish normally.
        executor.shutdown(cancel_futures=True)
    return results


def process_file(path: Path, job: Job) -> Result:
    """Add or remove the header in one file. Problems with the file become a FAILED result."""
    try:
        info = path.lstat()
    except FileNotFoundError:
        return Result(path, Status.SKIPPED, "file not found")
    except OSError as error:
        return _failed(path, error)
    if stat.S_ISLNK(info.st_mode):
        return Result(path, Status.SKIPPED, "symbolic link")
    if not stat.S_ISREG(info.st_mode):
        return Result(path, Status.SKIPPED, "not a regular file")

    language = job.types.for_name(path.name)
    if language is None and path.suffix:
        return Result(path, Status.SKIPPED, "unsupported file type")
    if info.st_size > MAX_FILE_SIZE:
        return Result(path, Status.SKIPPED, "larger than 10 MB")

    try:
        data = path.read_bytes()
    except OSError as error:
        return _failed(path, error)

    if language is None:
        # Without an extension, a #! line can still tell what the file is.
        first_line = data[:_SNIFF_SIZE].split(b"\n", 1)[0]
        language = language_from_shebang(first_line.decode("utf-8", "replace"))
        if language is None:
            return Result(path, Status.SKIPPED, "unsupported file type")
    if b"\0" in data[:_SNIFF_SIZE]:
        return Result(path, Status.SKIPPED, "binary file")

    bom = codecs.BOM_UTF8 if data.startswith(codecs.BOM_UTF8) else b""
    try:
        text = data[len(bom) :].decode("utf-8")
    except UnicodeDecodeError:
        return Result(path, Status.FAILED, "not UTF-8 text, left unchanged")

    try:
        if job.remove:
            new_text, status = job.header.remove(text, language)
        else:
            new_text, status = job.header.add(text, language, path.name, update=job.update)
    except PlacementError as error:
        return Result(path, Status.FAILED, str(error))
    if new_text is None:
        return Result(path, status)

    diff = _unified_diff(path, text, new_text) if job.diff else ""
    if job.write:
        try:
            write_atomic(path, bom + new_text.encode("utf-8"))
        except OSError as error:
            return _failed(path, error)
    return Result(path, status, diff=diff)


def _take(items: Iterator[Path], count: int) -> list[Path]:
    return [item for _, item in zip(range(count), items, strict=False)]


def _wait(future: Future[Result]) -> Result:
    # Waiting in short steps keeps Ctrl+C working on Windows.
    while True:
        try:
            return future.result(timeout=0.2)
        except TimeoutError:
            continue


def _failed(path: Path, error: OSError) -> Result:
    return Result(path, Status.FAILED, error.strerror or str(error))


def _unified_diff(path: Path, old: str, new: str) -> str:
    name = Path(display_path(path)).as_posix()
    lines = difflib.unified_diff(_split_lines(old), _split_lines(new), f"a/{name}", f"b/{name}")
    return "".join(
        line if line.endswith("\n") else line + "\n\\ No newline at end of file\n" for line in lines
    )


def _split_lines(text: str) -> list[str]:
    """Split at newlines only, keeping them. (str.splitlines also splits at \\f and others.)"""
    lines = [line + "\n" for line in text.split("\n")]
    lines[-1] = lines[-1][:-1]
    return lines if lines[-1] else lines[:-1]
