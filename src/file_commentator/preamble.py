"""Lines that must stay above a header, such as a #! line or an XML declaration."""

import enum
import re


class Preamble(enum.Flag):
    """Leading lines that a file type may have, which the header must go after.

    A ``#!`` line is always kept first, so it is not listed here.
    """

    NONE = 0
    CODING = enum.auto()  # Python and Ruby encoding comment: # -*- coding: utf-8 -*-
    XML = enum.auto()  # <?xml ...?> declaration and <!DOCTYPE ...>
    PHP = enum.auto()  # <?php opening tag; required, because text before it is output as-is
    CHARSET = enum.auto()  # CSS @charset rule, which must be the very first thing in the file
    DOCKER = enum.auto()  # Dockerfile parser directives, such as # syntax=...
    FRONT_MATTER = enum.auto()  # Markdown front matter between --- or +++ lines
    ECHO_OFF = enum.auto()  # @echo off at the top of a batch file


class PlacementError(Exception):
    """There is no safe place for a header in this file."""


_END = r"(?:\n|\Z)"
_SHEBANG = re.compile(r"#!(?!\[)[^\n]*" + _END)  # "#![" starts a Rust attribute, not a shebang
_CODING = re.compile(r"[ \t\f]*#[^\n]*?coding[:=][ \t]*[-\w.]+[^\n]*" + _END)
_XML_DECLARATION = re.compile(r"<\?xml\b.*?\?>[^\n]*" + _END, re.DOTALL)
_DOCTYPE = re.compile(r"[ \t]*<!DOCTYPE\b[^\n>]*>[^\n]*" + _END, re.IGNORECASE)
_PHP_OPEN = re.compile(r"<\?php\b(?![^\n]*\?>)[^\n]*" + _END, re.IGNORECASE)
_CHARSET = re.compile(r"@charset\b[^\n]*" + _END)
_DOCKER_DIRECTIVE = re.compile(r"#[ \t]*(?:syntax|escape|check)[ \t]*=[^\n]*" + _END, re.IGNORECASE)
_FRONT_MATTER = re.compile(
    r"(?:---[ \t]*\r?\n(?:.*?\n)??(?:---|\.\.\.)|\+\+\+[ \t]*\r?\n(?:.*?\n)??\+\+\+)[ \t]*\r?"
    + _END,
    re.DOTALL,
)
_ECHO_OFF = re.compile(r"@echo[ \t]+off[ \t]*\r?" + _END, re.IGNORECASE)
_BLANK_LINES = re.compile(r"(?:[ \t]*\r?\n)+")


def header_offset(text: str, preamble: Preamble) -> int:
    """Return the position in ``text`` where a header belongs.

    Raises PlacementError when the file has no safe place for one.
    """
    position = _skip(_SHEBANG, text, 0)
    if preamble & Preamble.CODING:
        position = _skip(_CODING, text, position)
    if preamble & Preamble.XML:
        position = _skip(_XML_DECLARATION, text, position)
        position = _skip(_DOCTYPE, text, position)
    if preamble & Preamble.PHP:
        match = _PHP_OPEN.match(text, position)
        if match is None:
            raise PlacementError(
                "the file does not start with a '<?php' line of its own, "
                "so there is no safe place for a header"
            )
        position = match.end()
    if preamble & Preamble.CHARSET:
        position = _skip(_CHARSET, text, position)
    if preamble & Preamble.DOCKER:
        while match := _DOCKER_DIRECTIVE.match(text, position):
            position = match.end()
    if preamble & Preamble.FRONT_MATTER:
        position = _skip(_FRONT_MATTER, text, position)
    if preamble & Preamble.ECHO_OFF:
        position = _skip(_ECHO_OFF, text, position)
    if position:
        # Blank lines after the preamble stay with it, above the header.
        position = _skip(_BLANK_LINES, text, position)
    return position


def _skip(pattern: re.Pattern[str], text: str, position: int) -> int:
    match = pattern.match(text, position)
    return match.end() if match else position
