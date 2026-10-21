import pytest

from file_commentator.preamble import PlacementError, Preamble, header_offset


@pytest.mark.parametrize(
    ("text", "preamble", "kept"),
    [
        ("code\n", Preamble.NONE, ""),
        ("#!/bin/sh\necho\n", Preamble.NONE, "#!/bin/sh\n"),
        ("#!/bin/sh", Preamble.NONE, "#!/bin/sh"),
        ("#!/bin/sh\n\n\necho\n", Preamble.NONE, "#!/bin/sh\n\n\n"),
        ("#![no_std]\n", Preamble.NONE, ""),
        ("# -*- coding: latin-1 -*-\nx\n", Preamble.CODING, "# -*- coding: latin-1 -*-\n"),
        ("#!/usr/bin/python\n# vim: set fileencoding=utf-8 :\nx\n", Preamble.CODING,
         "#!/usr/bin/python\n# vim: set fileencoding=utf-8 :\n"),
        ("# a comment\n# coding: utf-8\n", Preamble.CODING, ""),
        ('<?xml version="1.0"?>\n<a/>\n', Preamble.XML, '<?xml version="1.0"?>\n'),
        ("<!doctype html>\n<html>\n", Preamble.XML, "<!doctype html>\n"),
        ("<?php\nfoo();\n", Preamble.PHP, "<?php\n"),
        ("<?PHP\r\nfoo();\r\n", Preamble.PHP, "<?PHP\r\n"),
        ('@charset "utf-8";\na {}\n', Preamble.CHARSET, '@charset "utf-8";\n'),
        ("# syntax=x\n# escape=`\nFROM a\n", Preamble.DOCKER, "# syntax=x\n# escape=`\n"),
        ("# a comment\n# syntax=x\n", Preamble.DOCKER, ""),
        ("---\na: 1\n---\nText\n", Preamble.FRONT_MATTER, "---\na: 1\n---\n"),
        ("---\na: 1\n...\nText\n", Preamble.FRONT_MATTER, "---\na: 1\n...\n"),
        ("---\n---\nText\n", Preamble.FRONT_MATTER, "---\n---\n"),
        ("---\nnot closed\n", Preamble.FRONT_MATTER, ""),
        ("---\na: 1\n----\n", Preamble.FRONT_MATTER, ""),
        ("@ECHO OFF\r\necho\r\n", Preamble.ECHO_OFF, "@ECHO OFF\r\n"),
    ],
)  # fmt: skip
def test_header_goes_after_the_preamble(text: str, preamble: Preamble, kept: str) -> None:
    assert text[: header_offset(text, preamble)] == kept


@pytest.mark.parametrize("text", ["<html>\n<?php echo 1;\n", "<?php echo 1; ?>\n<p>\n", ""])
def test_php_without_an_opening_line_has_no_safe_place(text: str) -> None:
    with pytest.raises(PlacementError):
        header_offset(text, Preamble.PHP)
