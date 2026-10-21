import pytest
from conftest import language

from file_commentator.header import Header, Status
from file_commentator.preamble import PlacementError

PY = language("x.py")
C = language("x.c")


def test_adds_header_with_blank_line_after(header: Header) -> None:
    text, status = header.add('print("hi")\n', PY, "x.py")

    assert status is Status.ADDED
    assert text == (
        '# Copyright 2026 Example Corp\n# SPDX-License-Identifier: MIT\n\nprint("hi")\n'
    )


def test_adding_twice_changes_nothing(header: Header) -> None:
    once, _ = header.add("x = 1\n", PY, "x.py")
    assert once is not None

    assert header.add(once, PY, "x.py") == (None, Status.UNCHANGED)


@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("x.c", "/*\n * Copyright 2026 Example Corp\n * SPDX-License-Identifier: MIT\n */\n"),
        ("x.go", "// Copyright 2026 Example Corp\n// SPDX-License-Identifier: MIT\n"),
        ("x.sql", "-- Copyright 2026 Example Corp\n-- SPDX-License-Identifier: MIT\n"),
        ("x.html", "<!--\n  Copyright 2026 Example Corp\n  SPDX-License-Identifier: MIT\n-->\n"),
        ("x.ml", "(*\n * Copyright 2026 Example Corp\n * SPDX-License-Identifier: MIT\n *)\n"),
        ("x.j2", "{#\n  Copyright 2026 Example Corp\n  SPDX-License-Identifier: MIT\n#}\n"),
        ("x.bat", ":: Copyright 2026 Example Corp\n:: SPDX-License-Identifier: MIT\n"),
        ("x.vim", '" Copyright 2026 Example Corp\n" SPDX-License-Identifier: MIT\n'),
    ],
)
def test_uses_the_comment_style_of_each_language(
    header: Header, filename: str, expected: str
) -> None:
    text, _ = header.add("body\n", language(filename), filename)

    assert text == expected + "\nbody\n"


def test_empty_header_lines_have_no_trailing_whitespace() -> None:
    header = Header("Title\n\nBody")

    assert header.render(C.style, "x.c") == ["/*", " * Title", " *", " * Body", " */"]
    assert header.render(PY.style, "x.py") == ["# Title", "#", "# Body"]


def test_keeps_windows_line_endings(header: Header) -> None:
    text, _ = header.add("a = 1\r\nb = 2\r\n", PY, "x.py")

    assert text == (
        "# Copyright 2026 Example Corp\r\n# SPDX-License-Identifier: MIT\r\n\r\na = 1\r\nb = 2\r\n"
    )


def test_empty_file_gets_only_the_header(header: Header) -> None:
    text, _ = header.add("", PY, "x.py")

    assert text == "# Copyright 2026 Example Corp\n# SPDX-License-Identifier: MIT\n"


def test_finds_header_despite_trailing_spaces_and_crlf(header: Header) -> None:
    existing = "# Copyright 2026 Example Corp   \r\n# SPDX-License-Identifier: MIT\t\r\n\r\nx\r\n"

    assert header.add(existing, PY, "x.py") == (None, Status.UNCHANGED)


def test_finds_header_after_leading_blank_lines(header: Header) -> None:
    existing = "\n\n# Copyright 2026 Example Corp\n# SPDX-License-Identifier: MIT\n\nx\n"

    assert header.add(existing, PY, "x.py") == (None, Status.UNCHANGED)


def test_old_year_is_kept_unless_updating() -> None:
    old = Header("Copyright {year} Example", {"year": "2020"})
    new = Header("Copyright {year} Example", {"year": "2026"})
    text, _ = old.add("x = 1\n", PY, "x.py")
    assert text is not None

    assert new.add(text, PY, "x.py") == (None, Status.OUTDATED)
    updated, status = new.add(text, PY, "x.py", update=True)
    assert status is Status.UPDATED
    assert updated == "# Copyright 2026 Example\n\nx = 1\n"


def test_filename_placeholder() -> None:
    header = Header("File: {filename}")
    text, _ = header.add("x = 1\n", PY, "tool.py")
    assert text == "# File: tool.py\n\nx = 1\n"

    # A renamed file still has the header, with another value.
    assert header.add(text, PY, "renamed.py") == (None, Status.OUTDATED)


def test_custom_variables_and_unknown_placeholders() -> None:
    header = Header("(c) {author} {unknown}", {"author": "Jane Doe"})

    text, _ = header.add("x\n", PY, "x.py")

    assert text == "# (c) Jane Doe {unknown}\n\nx\n"
    assert header.add(text, PY, "x.py") == (None, Status.UNCHANGED)


def test_header_text_is_normalized() -> None:
    header = Header("\n\n  Indented line   \r\nNext\n\n")

    assert header.lines == ("  Indented line", "Next")


@pytest.mark.parametrize(
    ("text", "variables", "message"),
    [
        ("", {}, "empty"),
        ("\n  \n", {}, "empty"),
        ("{year} {filename}", {}, "fixed text"),
        ("{who}", {"who": "Jane"}, "fixed text"),
        ("Hi", {"bad-name": "x"}, "invalid variable name"),
        ("Hi", {"author": ""}, "single line"),
        ("Hi", {"author": "a\nb"}, "single line"),
    ],
)
def test_rejects_invalid_headers(text: str, variables: dict[str, str], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        Header(text, variables)


def test_refuses_text_that_would_close_the_comment() -> None:
    header = Header("Use */ carefully")

    with pytest.raises(PlacementError, match=r"\*/"):
        header.add("int x;\n", C, "x.c")
    assert header.add("x = 1\n", PY, "x.py")[1] is Status.ADDED


def test_xml_comments_cannot_contain_double_dash() -> None:
    header = Header("Copyright -- Example")

    with pytest.raises(PlacementError):
        header.add("<a/>\n", language("x.xml"), "x.xml")
    assert header.add("<p>\n", language("x.html"), "x.html")[1] is Status.ADDED


@pytest.mark.parametrize(
    ("filename", "original"),
    [
        ("x.py", "print(1)\n"),
        ("x.py", ""),
        ("x.py", "\n\nstarts with blank lines\n"),
        ("x.py", "no newline at the end"),
        ("x.py", "#!/usr/bin/env python3\nprint(1)\n"),
        ("x.py", "#!/usr/bin/env python3\n\nprint(1)\n"),
        ("x.py", "#!/usr/bin/env python3\n# -*- coding: utf-8 -*-\nprint(1)\n"),
        ("x.py", "a = 1\r\nb = 2\r\n"),
        ("x.c", "int main(void) { return 0; }\n"),
        ("x.php", "<?php\n\nnamespace App;\n"),
        ("x.php", "#!/usr/bin/env php\n<?php\necho 1;\n"),
        ("x.xml", '<?xml version="1.0"?>\n<!DOCTYPE note>\n<note/>\n'),
        ("x.html", "<!DOCTYPE html>\n<html></html>\n"),
        ("x.md", "---\ntitle: Hi\n---\n# Title\n"),
        ("x.md", "+++\ntitle = 'Hi'\n+++\n\n# Title\n"),
        ("x.css", '@charset "utf-8";\nbody {}\n'),
        ("Dockerfile", "# syntax=docker/dockerfile:1\n# escape=`\nFROM alpine\n"),
        ("x.bat", "@echo off\r\necho hi\r\n"),
        ("x.rs", "#![allow(dead_code)]\nfn main() {}\n"),
    ],
)
def test_remove_undoes_add_exactly(header: Header, filename: str, original: str) -> None:
    lang = language(filename)
    added, status = header.add(original, lang, filename)
    assert status is Status.ADDED
    assert added is not None

    removed, status = header.remove(added, lang)

    assert status is Status.REMOVED
    assert removed == original


def test_remove_without_header_changes_nothing(header: Header) -> None:
    assert header.remove("x = 1\n", PY) == (None, Status.UNCHANGED)


def test_remove_ignores_files_where_no_header_could_be_added(header: Header) -> None:
    assert header.remove("<html><?php echo 1; ?>\n", language("x.php")) == (
        None,
        Status.UNCHANGED,
    )


def test_remove_matches_any_placeholder_values() -> None:
    text = "# Copyright 2019 Example Corp\n# SPDX-License-Identifier: MIT\n\nx = 1\n"
    header = Header("Copyright {year} Example Corp\nSPDX-License-Identifier: MIT")

    assert header.remove(text, PY) == ("x = 1\n", Status.REMOVED)
