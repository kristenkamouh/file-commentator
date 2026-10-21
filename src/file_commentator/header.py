"""Header templates, and adding, finding, and removing them in a file's text."""

import datetime
import enum
import re
from collections.abc import Mapping

from file_commentator.languages import CommentStyle, Language
from file_commentator.preamble import PlacementError, header_offset

_PLACEHOLDER = re.compile(r"\{(\w+)\}")
_NEWLINE = re.compile(r"\r?\n")
_BLANK_LINE = re.compile(r"[ \t]*\r?\n")


class Status(enum.Enum):
    """The outcome for one file."""

    ADDED = "added"
    UPDATED = "updated"
    REMOVED = "removed"
    UNCHANGED = "unchanged"
    OUTDATED = "outdated"  # has the header, but with other placeholder values (an older year)
    SKIPPED = "skipped"  # not a file this tool handles: binary, unknown type, and so on
    FAILED = "failed"


class Header:
    """A header template: plain text whose lines may contain placeholders.

    ``{year}`` and ``{filename}`` are built in. ``variables`` adds more, or overrides them.
    Placeholders that are not defined are kept as written.
    """

    def __init__(self, text: str, variables: Mapping[str, str] | None = None) -> None:
        lines = [
            line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        ]
        while lines and not lines[0]:
            lines.pop(0)
        while lines and not lines[-1]:
            lines.pop()
        if not lines:
            raise ValueError("the header text is empty")

        self.variables = {"year": str(datetime.date.today().year)}
        for name, value in (variables or {}).items():
            if not re.fullmatch(r"\w+", name):
                raise ValueError(
                    f"invalid variable name '{name}': use letters, digits, and underscores"
                )
            value = value.strip()
            if not value or "\n" in value or "\r" in value:
                raise ValueError(f"variable '{name}' must be a single line of text")
            self.variables[name] = value

        self._known = frozenset({"filename", *self.variables})
        fixed_text = _PLACEHOLDER.sub(
            lambda m: "" if m.group(1) in self._known else m.group(0), "\n".join(lines)
        )
        if not fixed_text.strip():
            # A header made only of placeholders would match any comment.
            raise ValueError("the header needs some fixed text besides placeholders")

        self.lines = tuple(lines)
        self._patterns: dict[str, re.Pattern[str]] = {}

    def render(self, style: CommentStyle, filename: str) -> list[str]:
        """Return the header as comment lines for one file."""
        values = {"filename": filename, **self.variables}
        lines = [
            _PLACEHOLDER.sub(lambda m: values.get(m.group(1), m.group(0)), line)
            for line in self.lines
        ]
        for token in style.forbidden:
            if any(token in line for line in lines):
                raise PlacementError(
                    f"the header contains '{token}', which cannot appear inside "
                    f"a {style.sample()} comment"
                )
        return style.render(lines)

    def add(
        self, text: str, language: Language, filename: str, *, update: bool = False
    ) -> tuple[str | None, Status]:
        """Add the header to a file's text.

        Returns the new text, or None when nothing changes, and what happened. A header
        that is already there with other placeholder values is replaced only if ``update``.
        """
        offset = header_offset(text, language.preamble)
        lines = self.render(language.style, filename)
        newline = _detect_newline(text)

        match = self._pattern(language.style).match(text, offset)
        if match:
            existing = [line.rstrip() for line in _NEWLINE.split(match.group(2))]
            if existing == lines:
                return None, Status.UNCHANGED
            if not update:
                return None, Status.OUTDATED
            new_text = text[: match.start(2)] + newline.join(lines) + text[match.end(2) :]
            return new_text, Status.UPDATED

        before, after = text[:offset], text[offset:]
        if before and not before.endswith("\n"):
            before += newline
        block = newline.join(lines) + newline
        if after:
            block += newline  # a blank line between the header and the code
        return before + block + after, Status.ADDED

    def remove(self, text: str, language: Language) -> tuple[str | None, Status]:
        """Remove the header, and the blank line after it, from a file's text."""
        try:
            offset = header_offset(text, language.preamble)
        except PlacementError:
            return None, Status.UNCHANGED  # a header could never have been added here
        match = self._pattern(language.style).match(text, offset)
        if match is None:
            return None, Status.UNCHANGED
        after = text[match.end() :]
        blank = _BLANK_LINE.match(after)
        if blank:
            after = after[blank.end() :]
        return text[:offset] + match.group(1) + after, Status.REMOVED

    def _pattern(self, style: CommentStyle) -> re.Pattern[str]:
        pattern = self._patterns.get(style.name)
        if pattern is None:
            pattern = self._patterns[style.name] = self._compile(style)
        return pattern

    def _compile(self, style: CommentStyle) -> re.Pattern[str]:
        """Build a regex that finds this header in a file, whatever its placeholder values are.

        Group 1 is any blank lines before the header, group 2 is the header itself.
        Trailing whitespace and either kind of line ending are accepted.
        """
        lines = []
        for line in style.render(self.lines):
            parts, end = [], 0
            for match in _PLACEHOLDER.finditer(line):
                if match.group(1) in self._known:
                    parts += [re.escape(line[end : match.start()]), r"[^\r\n]*?"]
                    end = match.end()
            parts.append(re.escape(line[end:]))
            lines.append("".join(parts) + r"[ \t]*")
        return re.compile(r"((?:[ \t]*\r?\n)*)(" + r"\r?\n".join(lines) + r")\r?(?:\n|\Z)")


def _detect_newline(text: str) -> str:
    """Return the line ending the file uses, judged by its first line."""
    index = text.find("\n")
    return "\r\n" if index > 0 and text[index - 1] == "\r" else "\n"
