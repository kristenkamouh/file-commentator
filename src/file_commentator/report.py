"""Everything the tool prints: progress, per-file lines, summaries, and the list of styles."""

import shutil
import sys
import textwrap
import time
from collections import Counter
from collections.abc import Sequence

from file_commentator.files import Discovery, display_path
from file_commentator.header import Status
from file_commentator.languages import BUILTIN_TYPES, STYLES
from file_commentator.runner import Result

# How each command describes a file that changes: (when written, when previewed).
_CHANGE_LABELS = {
    "add": {Status.ADDED: ("added", "would add"), Status.UPDATED: ("updated", "would update")},
    "check": {Status.ADDED: ("missing", "missing"), Status.UPDATED: ("outdated", "outdated")},
    "remove": {Status.REMOVED: ("removed", "would remove")},
}


class Progress:
    """A one-line progress bar on stderr.

    It only shows on a terminal, once the work has taken half a second, and is redrawn
    at most ten times a second.
    """

    def __init__(self, enabled: bool = True) -> None:
        self._enabled = enabled and sys.stderr.isatty()
        self._started = time.monotonic()
        self._drawn_at = 0.0
        self._width = 0

    def update(self, done: int, total: int) -> None:
        if not self._enabled:
            return
        now = time.monotonic()
        if now - self._started < 0.5 or (now - self._drawn_at < 0.1 and done < total):
            return
        self._drawn_at = now
        filled = 30 * done // total
        line = f"[{'#' * filled}{'-' * (30 - filled)}] {done}/{total} files"
        sys.stderr.write("\r" + line)
        sys.stderr.flush()
        self._width = len(line)

    def clear(self) -> None:
        if self._width:
            sys.stderr.write("\r" + " " * self._width + "\r")
            sys.stderr.flush()
            self._width = 0


def print_report(
    command: str,
    results: Sequence[Result],
    discovery: Discovery,
    *,
    preview: bool,
    verbose: bool = False,
    quiet: bool = False,
    diff: bool = False,
) -> None:
    """Print errors, the files that changed or would change, and a summary.

    Changed files are listed when previewing, when checking, or with ``verbose``;
    otherwise only the summary is printed. Errors are always printed.
    """
    print_errors(results, discovery)
    if quiet:
        return
    labels = _CHANGE_LABELS[command]
    for result in results:
        path = display_path(result.path)
        if result.status in labels:
            if diff:
                write_raw(result.diff)
            elif preview or verbose or command == "check":
                written, previewed = labels[result.status]
                print(f"{previewed if preview else written:<13}{path}")
        elif verbose and result.status is not Status.FAILED:
            print(f"{_state_label(result.status):<13}{path}{_state_detail(result)}")
    sys.stdout.flush()  # so the summary comes last even when stdout is a pipe
    print(summarize(command, results, discovery, preview=preview), file=sys.stderr)


def print_errors(results: Sequence[Result], discovery: Discovery) -> None:
    """Print folders that could not be read and files that failed, to stderr."""
    for path, message in discovery.errors:
        print(f"error: {display_path(path)}: {message}", file=sys.stderr)
    for result in results:
        if result.status is Status.FAILED:
            print(f"error: {display_path(result.path)}: {result.detail}", file=sys.stderr)


def summarize(
    command: str, results: Sequence[Result], discovery: Discovery, *, preview: bool
) -> str:
    """Describe the outcome in a sentence or two."""
    if not results:
        if discovery.used_git:
            return (
                "No files found. Files ignored by git are left out; "
                "use --no-gitignore to include them."
            )
        return "No files found."
    counts = Counter(result.status for result in results)
    if counts[Status.SKIPPED] == len(results):
        return (
            f"No supported files found ({plural(len(results), 'file')} skipped). Use -v to see "
            "why, or --style to set the comment style for a file type."
        )

    unchanged = counts[Status.UNCHANGED]
    outdated = counts[Status.OUTDATED]
    details = []
    advice = ""
    if command == "add":
        added, updated = counts[Status.ADDED], counts[Status.UPDATED]
        changes = []
        if added:
            changes.append(f"{'would add' if preview else 'added'} the header to {plural(added)}")
        if updated:
            changes.append(f"{'would update' if preview else 'updated'} it in {plural(updated)}")
        headline = " and ".join(changes) or "no files needed the header"
        if unchanged:
            details.append(f"{plural(unchanged)} already {_have(unchanged)} it")
        if outdated:
            details.append(f"{plural(outdated)} {_have(outdated)} it with other values")
            advice = "Use --update to refresh headers with other values."
    elif command == "check":
        missing, stale = counts[Status.ADDED], counts[Status.UPDATED]
        problems = []
        if missing:
            problems.append(f"{plural(missing)} missing the header")
        if stale:
            problems.append(f"{plural(stale)} with an outdated header")
        if problems:
            headline = " and ".join(problems)
            advice = f"Run 'commentator add{' --update' if stale else ''}' to fix them."
        elif unchanged + outdated:
            headline = f"all files have the header ({plural(unchanged + outdated)} checked)"
        else:
            headline = "no files to check"
    else:
        removed = counts[Status.REMOVED]
        verb = "would remove" if preview else "removed"
        headline = f"{verb} the header from {plural(removed)}" if removed else "no files had it"
        if unchanged:
            details.append(f"{plural(unchanged)} did not have it")

    if counts[Status.SKIPPED]:
        details.append(f"{plural(counts[Status.SKIPPED])} skipped")
    if counts[Status.FAILED]:
        details.append(f"{plural(counts[Status.FAILED])} failed")
    sentences = [headline, ", ".join(details), advice]
    return " ".join(capitalize(s).rstrip(".") + "." for s in sentences if s)


def exit_code(command: str, results: Sequence[Result], discovery: Discovery) -> int:
    """1 if anything failed, or if ``check`` found files to fix; otherwise 0."""
    if discovery.errors or any(result.status is Status.FAILED for result in results):
        return 1
    if command == "check" and any(
        result.status in (Status.ADDED, Status.UPDATED) for result in results
    ):
        return 1
    return 0


def print_styles() -> None:
    """Print the comment styles and the built-in file types."""
    print("Comment styles, for --style GLOB=STYLE or the [styles] setting:\n")
    for style in STYLES.values():
        print(f"  {style.name:<12}{style.sample()}")
    print("\nBuilt-in file types:\n")
    width = max(60, shutil.get_terminal_size().columns - 1)
    for language, patterns in BUILTIN_TYPES:
        lead = f"  {language.name:<20}{language.style.name:<12}"
        lines = textwrap.wrap(" ".join(patterns), width - len(lead))
        print(lead + lines[0])
        for line in lines[1:]:
            print(" " * len(lead) + line)
    print("\nFiles without an extension are recognized by their #! line, such as #!/bin/sh.")


def write_raw(text: str) -> None:
    """Write to stdout as UTF-8 with line endings untouched, so a diff stays a valid patch."""
    sys.stdout.flush()
    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is None:
        sys.stdout.write(text)
    else:
        buffer.write(text.encode("utf-8"))
        buffer.flush()


def plural(count: int, noun: str = "file") -> str:
    return f"{count} {noun}" if count == 1 else f"{count} {noun}s"


def _have(count: int) -> str:
    return "has" if count == 1 else "have"


def capitalize(text: str) -> str:
    return text[:1].upper() + text[1:]


def _state_label(status: Status) -> str:
    return "unchanged" if status in (Status.UNCHANGED, Status.OUTDATED) else status.value


def _state_detail(result: Result) -> str:
    if result.detail:
        return f" ({result.detail})"
    if result.status is Status.OUTDATED:
        return " (has the header with other values)"
    return ""
