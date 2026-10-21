"""Guided mode, used when the tool runs in a terminal without arguments."""

import dataclasses
from collections.abc import Sequence
from pathlib import Path

from file_commentator import __version__
from file_commentator.config import ConfigError, read_text
from file_commentator.files import Discovery, Selection, display_path, find_files, split_patterns
from file_commentator.header import Header, Status
from file_commentator.languages import FileTypes
from file_commentator.report import (
    Progress,
    capitalize,
    exit_code,
    plural,
    print_errors,
    summarize,
    write_raw,
)
from file_commentator.runner import Job, Result, process_file, run

CANCELLED = 130


def run_wizard() -> int:
    """Ask for a folder, a header, and file patterns, preview the change, then apply it."""
    print(f"file-commentator {__version__}: add a header comment to the top of files.")
    print("Press Ctrl+C at any time to cancel.")
    try:
        folder = _ask_folder()
        header = _ask_header()
        include = _ask_patterns()

        print("\nLooking for files...")
        discovery = find_files([folder], Selection(include=include))
        job = Job(header, FileTypes(), write=False)
        planned = _run_with_progress(discovery.files, job)
        print_errors(planned, discovery)
        print(summarize("add", planned, discovery, preview=True))
        to_change = [result.path for result in planned if result.status is Status.ADDED]
        if not to_change:
            return exit_code("add", planned, discovery)

        sample = process_file(to_change[0], dataclasses.replace(job, diff=True))
        print(f"\nThe change for {display_path(to_change[0])}:\n")
        write_raw(sample.diff)
        answer = input(f"\nAdd the header to {plural(len(to_change))}? [y/N]: ")
        if answer.strip().lower() not in ("y", "yes"):
            print("Cancelled. No files were changed.")
            return 0
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled. No files were changed.")
        return CANCELLED

    results = _run_with_progress(to_change, dataclasses.replace(job, write=True))
    print_errors(results, Discovery())
    print(summarize("add", results, Discovery(), preview=False))
    return exit_code("add", results, Discovery())


def _ask_folder() -> Path:
    while True:
        answer = _clean(input("\nFolder to process (press Enter for the current folder): "))
        folder = Path(answer or ".").expanduser()
        if folder.is_dir():
            return folder
        print(f"'{answer}' is not a folder.")


def _ask_header() -> Header:
    print(
        "\nThe header is plain text. Comment markers such as #, // or /* */ are added to fit "
        "each file type.\n{year} and {filename} are replaced with the current year and the "
        "file's name."
    )
    while True:
        answer = _clean(input("Path of a text file with the header (press Enter to type it): "))
        if answer:
            try:
                text = read_text(Path(answer).expanduser())
            except ConfigError as error:
                print(f"{capitalize(str(error))}.")
                continue
        else:
            print("Type the header. Finish with a line that contains only a period (.):")
            lines = []
            while (line := input()).strip() != ".":
                lines.append(line)
            text = "\n".join(lines)
        try:
            return Header(text)
        except ValueError as error:
            print(f"{capitalize(str(error))}. Please try again.")


def _ask_patterns() -> tuple[str, ...]:
    answer = input(
        "\nOnly process files matching these patterns, comma-separated (for example "
        "*.py,*.js).\nPress Enter for all supported files: "
    )
    return tuple(split_patterns([answer]))


def _run_with_progress(files: Sequence[Path], job: Job) -> list[Result]:
    progress = Progress()
    try:
        return run(files, job, on_progress=progress.update)
    finally:
        progress.clear()


def _clean(answer: str) -> str:
    """Trim spaces and the quotes that "Copy as path" adds on Windows."""
    return answer.strip().strip('"').strip("'").strip()
