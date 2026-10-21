"""The command-line interface."""

import argparse
import io
import sys
from collections.abc import Sequence
from pathlib import Path

from file_commentator import __version__
from file_commentator.config import Config, ConfigError, find_config, load_config, read_text
from file_commentator.files import Selection, find_files, split_patterns
from file_commentator.header import Header
from file_commentator.languages import FileTypes
from file_commentator.report import Progress, exit_code, print_report, print_styles
from file_commentator.runner import Job, run
from file_commentator.wizard import run_wizard

EXIT_USAGE = 2
EXIT_INTERRUPTED = 130


class UsageError(Exception):
    """A problem with the options or settings, found before any file is touched."""


def main(argv: Sequence[str] | None = None) -> int:
    """Run the tool and return its exit code."""
    # Never crash on a file name the console cannot show.
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(errors="replace")
    arguments = list(sys.argv[1:] if argv is None else argv)
    try:
        if not arguments and sys.stdin.isatty() and sys.stdout.isatty():
            return run_wizard()
        parser = build_parser()
        args = parser.parse_args(arguments)
        if args.command is None:
            parser.print_help(sys.stderr)
            return EXIT_USAGE
        if args.command == "styles":
            print_styles()
            return 0
        return _run(args)
    except UsageError as error:
        print(f"commentator: error: {error}", file=sys.stderr)
        return EXIT_USAGE
    except KeyboardInterrupt:
        print(
            "\nInterrupted. Files already written are complete; the others were not changed.",
            file=sys.stderr,
        )
        return EXIT_INTERRUPTED


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="commentator",
        description="Add, check, or remove a header comment at the top of files.",
        epilog="Run 'commentator COMMAND --help' for the options of a command. "
        "Run 'commentator' with no arguments in a terminal for guided mode.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command", title="commands", metavar="COMMAND")

    selection = argparse.ArgumentParser(add_help=False)
    selection.add_argument(
        "paths",
        nargs="*",
        type=Path,
        metavar="PATH",
        help="files or folders to process (default: the current folder)",
    )
    group = selection.add_argument_group("choosing files")
    group.add_argument(
        "--include",
        action="append",
        default=[],
        metavar="GLOB",
        help="only process files matching GLOB, such as '*.py' (repeatable, or comma-separated)",
    )
    group.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="GLOB",
        help="skip files and folders matching GLOB (repeatable, or comma-separated)",
    )
    group.add_argument(
        "--style",
        action="append",
        default=[],
        metavar="GLOB=STYLE",
        help="comment style for files matching GLOB, such as '*.txt=hash' (repeatable)",
    )
    group.add_argument(
        "--no-gitignore",
        action="store_true",
        help="also process files that .gitignore leaves out",
    )
    group.add_argument(
        "--config",
        type=Path,
        metavar="FILE",
        help="read settings from FILE instead of looking for .commentator.toml or pyproject.toml",
    )

    header = argparse.ArgumentParser(add_help=False)
    group = header.add_argument_group("header")
    source = group.add_mutually_exclusive_group()
    source.add_argument("--header", metavar="TEXT", help="the header text, without comment markers")
    source.add_argument(
        "--header-file", type=Path, metavar="FILE", help="read the header from FILE"
    )
    group.add_argument(
        "--var",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help="value for a {NAME} placeholder in the header (repeatable)",
    )

    output = argparse.ArgumentParser(add_help=False)
    group = output.add_argument_group("output")
    level = group.add_mutually_exclusive_group()
    level.add_argument("-q", "--quiet", action="store_true", help="print errors only")
    level.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="list every file, including unchanged and skipped ones",
    )

    shared = [selection, header, output]
    add = commands.add_parser(
        "add",
        parents=shared,
        help="add the header to files that do not have it",
        description="Add the header to files that do not have it yet.",
    )
    add.add_argument(
        "--update",
        action="store_true",
        help="also rewrite headers whose placeholder values differ, such as an older {year}",
    )
    _add_preview_options(add)

    check = commands.add_parser(
        "check",
        parents=shared,
        help="report files without the header, with exit code 1 if there are any",
        description="Report files that do not have the header, without changing them. "
        "Exits with code 1 if there are any, which makes it suitable for CI.",
    )
    check.add_argument(
        "--update",
        action="store_true",
        help="also report headers whose placeholder values differ",
    )
    check.add_argument("--diff", action="store_true", help="show the changes 'add' would make")
    check.set_defaults(dry_run=False)

    remove = commands.add_parser(
        "remove",
        parents=shared,
        help="remove the header from files",
        description="Remove the header, and the blank line after it, from files.",
    )
    _add_preview_options(remove)
    remove.set_defaults(update=False)

    commands.add_parser(
        "styles",
        help="list the comment styles and the file types that use them",
        description="List the comment styles and the file types that use them.",
    )
    return parser


def _add_preview_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="list the files that would change, without changing them",
    )
    parser.add_argument(
        "--diff",
        action="store_true",
        help="show the changes as a diff, without changing any file",
    )


def _run(args: argparse.Namespace) -> int:
    config = _load_config(args.config)
    job = Job(
        header=_header(args, config),
        types=_file_types(args, config),
        remove=args.command == "remove",
        update=args.update,
        write=args.command != "check" and not args.dry_run and not args.diff,
        diff=args.diff,
    )
    selection = Selection(
        include=tuple(split_patterns(args.include) or config.include),
        exclude=tuple(config.exclude + split_patterns(args.exclude)),
    )
    paths = args.paths or [Path()]
    for path in paths:
        if not path.exists():
            raise UsageError(f"no such file or folder: {path}")

    discovery = find_files(paths, selection, gitignore=config.gitignore and not args.no_gitignore)
    progress = Progress(enabled=not args.quiet)
    try:
        results = run(discovery.files, job, on_progress=progress.update)
    finally:
        progress.clear()
    print_report(
        args.command,
        results,
        discovery,
        preview=args.command != "check" and not job.write,
        verbose=args.verbose,
        quiet=args.quiet,
        diff=args.diff,
    )
    return exit_code(args.command, results, discovery)


def _load_config(path: Path | None) -> Config:
    try:
        if path is None:
            path = find_config(Path.cwd())
            if path is None:
                return Config()
        return load_config(path)
    except ConfigError as error:
        raise UsageError(str(error)) from None


def _header(args: argparse.Namespace, config: Config) -> Header:
    if args.header is not None:
        text = args.header
    elif args.header_file is not None:
        try:
            text = read_text(args.header_file)
        except ConfigError as error:
            raise UsageError(str(error)) from None
    elif config.header is not None:
        text = config.header
    else:
        raise UsageError(
            "no header given. Use --header TEXT or --header-file FILE, "
            "or set 'header' in .commentator.toml"
        )
    variables = {**config.variables, **_pairs(args.var, "--var", "NAME=VALUE")}
    try:
        return Header(text, variables)
    except ValueError as error:
        raise UsageError(str(error)) from None


def _file_types(args: argparse.Namespace, config: Config) -> FileTypes:
    styles = dict(config.styles)
    for pattern, style in _pairs(args.style, "--style", "GLOB=STYLE", split_at_last=True).items():
        styles.pop(pattern, None)
        styles[pattern] = style  # entries from the command line go last, so they win
    try:
        return FileTypes(styles)
    except ValueError as error:
        raise UsageError(str(error)) from None


def _pairs(
    values: Sequence[str], option: str, form: str, *, split_at_last: bool = False
) -> dict[str, str]:
    """Parse KEY=VALUE options. --style splits at the last '=', as a glob comes first."""
    pairs = {}
    for value in values:
        name, equals, rest = value.rpartition("=") if split_at_last else value.partition("=")
        if not equals or not name.strip():
            raise UsageError(f"{option} expects {form}, got '{value}'")
        pairs[name.strip()] = rest
    return pairs
