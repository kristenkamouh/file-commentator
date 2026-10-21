from collections import Counter

import pytest

from file_commentator.languages import (
    BUILTIN_TYPES,
    STYLES,
    FileTypes,
    builtin_language,
    language_from_shebang,
)
from file_commentator.preamble import Preamble


@pytest.mark.parametrize(
    ("filename", "name"),
    [
        ("main.py", "Python"),
        ("MAIN.PY", "Python"),
        ("index.d.ts", "TypeScript"),
        ("Makefile", "Makefile"),
        ("makefile", "Makefile"),
        ("Dockerfile", "Dockerfile"),
        ("Dockerfile.dev", "Dockerfile"),
        ("CMakeLists.txt", "CMake"),
        ("requirements-dev.txt", "Config files"),
        (".env.local", "Config files"),
        (".bashrc", "Shell"),
        ("Jenkinsfile", "Groovy"),
    ],
)
def test_builtin_lookup(filename: str, name: str) -> None:
    found = builtin_language(filename)

    assert found is not None
    assert found.name == name


@pytest.mark.parametrize("filename", ["logo.png", "notes.txt", "data.json", "model.m", "LICENSE"])
def test_unknown_or_ambiguous_types_are_not_guessed(filename: str) -> None:
    assert builtin_language(filename) is None


def test_no_pattern_belongs_to_two_languages() -> None:
    patterns = Counter(p.lower() for _, group in BUILTIN_TYPES for p in group)

    assert [p for p, count in patterns.items() if count > 1] == []


def test_overrides_add_types_and_keep_preamble_rules() -> None:
    types = FileTypes({"*.txt": "hash", "*.py": "slash"})

    txt = types.for_name("notes.txt")
    py = types.for_name("main.py")

    assert txt is not None and txt.style is STYLES["hash"]
    assert py is not None and py.style is STYLES["slash"]
    assert py.preamble is Preamble.CODING


def test_later_overrides_win() -> None:
    types = FileTypes({"*.txt": "hash", "notes.txt": "dash"})

    notes = types.for_name("notes.txt")
    other = types.for_name("other.txt")

    assert notes is not None and notes.style is STYLES["dash"]
    assert other is not None and other.style is STYLES["hash"]


def test_unknown_style_is_an_error() -> None:
    with pytest.raises(ValueError, match="unknown comment style 'pound'"):
        FileTypes({"*.txt": "pound"})


@pytest.mark.parametrize(
    ("line", "name"),
    [
        ("#!/bin/sh", "Shell"),
        ("#!/usr/bin/env bash", "Shell"),
        ("#!/usr/bin/env python3.12", "Python"),
        ("#!/usr/bin/env -S python3 -u", "Python"),
        ("#! /usr/local/bin/node", "JavaScript"),
        ("#!/usr/bin/env FOO=1 ruby", "Ruby"),
    ],
)
def test_language_from_shebang(line: str, name: str) -> None:
    found = language_from_shebang(line)

    assert found is not None
    assert found.name == name


@pytest.mark.parametrize("line", ["", "#!", "#!/usr/bin/env", "#!/opt/custom-tool", "#![attr]"])
def test_no_language_from_unknown_shebang(line: str) -> None:
    assert language_from_shebang(line) is None
