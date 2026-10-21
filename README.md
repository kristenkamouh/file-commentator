# file-commentator

file-commentator adds a header comment to the top of every file in a project: a license
notice, a copyright line, author details, or any other text. You write the header once
as plain text, and it is turned into the right comment syntax for each file type.

```console
$ commentator add --header "Copyright {year} Example Corp
SPDX-License-Identifier: MIT"
Added the header to 42 files. 3 files skipped.
```

```python
# Copyright 2026 Example Corp
# SPDX-License-Identifier: MIT

import os
```

```c
/*
 * Copyright 2026 Example Corp
 * SPDX-License-Identifier: MIT
 */

#include <stdio.h>
```

- Knows the comment syntax of 65 file types, and any other type can be mapped to one
  of 15 comment styles.
- Puts the header after lines that must stay first, such as `#!/bin/sh`,
  `<?xml ...?>`, and `<?php`.
- Leaves binary and non-UTF-8 files alone, and keeps line endings, byte order marks,
  and file permissions as they were.
- Checks for missing headers in CI, removes headers, and updates them when the
  year changes.
- Follows `.gitignore`, works on many files in parallel, and has no dependencies.

## Installation

file-commentator needs Python 3.11 or newer.

```console
pipx install git+https://github.com/kristenkamouh/file-commentator.git
```

`pip install git+https://github.com/kristenkamouh/file-commentator.git` works too. Either
way, you get the `commentator` command, which you can also run as
`python -m file_commentator`.

## Quick start

Write the header to a file, for example `HEADER.txt`:

```text
Copyright {year} Example Corp
SPDX-License-Identifier: MIT
```

Then, from the root of your project:

```console
commentator add --header-file HEADER.txt --diff      # preview the changes
commentator add --header-file HEADER.txt             # add the header where it is missing
commentator check --header-file HEADER.txt           # exit code 1 if any file lacks it
commentator remove --header-file HEADER.txt          # take it out again
```

To avoid repeating options, put them in a [settings file](#settings-file). Then
`commentator add` and `commentator check` need no options at all.

Run `commentator` with no arguments in a terminal for guided mode, which asks for the
folder, the header, and the file types, shows a preview, and asks before changing
anything.

## Commands

| Command | What it does |
| --- | --- |
| `commentator add [PATH ...]` | Adds the header to files that do not have it. |
| `commentator check [PATH ...]` | Lists files without the header and exits with code 1 if there are any. Changes nothing. |
| `commentator remove [PATH ...]` | Removes the header, and the blank line after it. |
| `commentator styles` | Lists the comment styles and the file types that use them. |

`PATH` can be files or folders, and defaults to the current folder.

| Option | Commands | Meaning |
| --- | --- | --- |
| `--header TEXT` | all | The header text, without comment markers. |
| `--header-file FILE` | all | Read the header from a UTF-8 text file. |
| `--var NAME=VALUE` | all | Value for a `{NAME}` placeholder. Repeatable. |
| `--include GLOB` | all | Only process files matching `GLOB`, such as `'*.py'`. Repeatable or comma-separated. |
| `--exclude GLOB` | all | Skip files and folders matching `GLOB`. Repeatable or comma-separated. |
| `--style GLOB=STYLE` | all | Comment style for matching files, such as `'*.txt=hash'`. Repeatable. |
| `--no-gitignore` | all | Also process files that `.gitignore` leaves out. |
| `--config FILE` | all | Read settings from `FILE` instead of searching for them. |
| `--update` | `add`, `check` | Also rewrite (or, for `check`, report) headers whose placeholder values differ. |
| `--dry-run` | `add`, `remove` | List the files that would change, without changing them. |
| `--diff` | all | Print the changes as a unified diff, without changing any file. |
| `-v`, `--verbose` | all | List every file, including unchanged and skipped ones, with the reason. |
| `-q`, `--quiet` | all | Print errors only. |

## The header

The header is plain text. file-commentator adds the comment markers, so the same header
works for Python, C, HTML, SQL, and the rest. Blank lines at the start and end of the
text, and spaces at the end of lines, are removed.

These placeholders are filled in for each file:

| Placeholder | Value |
| --- | --- |
| `{year}` | The current year. |
| `{filename}` | The file's name, such as `main.py`. |
| `{NAME}` | Anything you define with `--var NAME=VALUE` or in `[variables]`. |

Your own variables can also replace `{year}`, for example `--var year=2019`. Text in
braces that is not a defined placeholder is kept as written.

### How existing headers are found

A file already has the header if the header appears right where file-commentator would put
it, with any values in the placeholders. Differences in line endings, trailing spaces,
and blank lines before the header do not matter.

This means `add` does not touch a file whose header says `Copyright 2024` when the
current year is 2026, which keeps the original year of each file. To refresh such
headers, run `add --update`. `remove` removes the header whatever its placeholder
values are.

Because placeholders match any text, a header such as `Copyright {year} {author}` also
matches someone else's `Copyright 2019 Other Corp` line. Run with `--diff` first when
using `--update` or `remove` with placeholders.

To change the wording of a header, remove the old one, then add the new one:

```console
commentator remove --header-file OLD_HEADER.txt
commentator add --header-file HEADER.txt
```

### Where the header goes

The header goes at the very top of the file, followed by one blank line, except when
the file starts with lines that must stay first. The header then goes below those
lines, and below any blank lines that follow them:

| File type | Lines kept above the header |
| --- | --- |
| Any | A `#!` line, such as `#!/usr/bin/env python3` |
| Python, Ruby | An encoding comment, such as `# -*- coding: utf-8 -*-` |
| XML, HTML | `<?xml ...?>` and `<!DOCTYPE ...>` |
| PHP | The `<?php` line. Files that do not start with one are reported and left unchanged, since text before it would become page output. |
| CSS | `@charset "...";` |
| Dockerfile | Parser directives, such as `# syntax=docker/dockerfile:1` |
| Markdown | Front matter between `---` or `+++` lines |
| Batch | `@echo off` |

## Choosing files

When a folder is part of a git repository, file-commentator asks git for its files, so
everything in `.gitignore` is left out. Outside a repository, or with
`--no-gitignore`, it lists the folder itself and skips these folders:

`.git` `.hg` `.svn` `node_modules` `__pycache__` `.venv` `venv` `.tox` `.nox`
`.mypy_cache` `.pytest_cache` `.ruff_cache` `.idea` `.vscode` `dist` `build` `target`
`*.egg-info`

Inside a repository, those folders are only skipped for files that git does not track.

`--include` and `--exclude` take glob patterns:

- A pattern without a slash matches a file or folder name anywhere: `*.py`, `vendor`,
  `*.min.js`.
- A pattern with a slash matches a path from the current folder: `src/legacy`,
  `tests/fixtures/*`. Here `*` also matches slashes.

These files are skipped, and listed with `-v`:

- File types without a known comment style. Use `--style` to add one.
- Binary files, symbolic links, and files larger than 10 MB.

Files that are not valid UTF-8 text, and files where a header cannot be placed safely,
are reported as errors and left unchanged.

## File types and comment styles

Run `commentator styles` for the full list. The styles are:

| Style | Looks like | Used for, among others |
| --- | --- | --- |
| `hash` | `# ...` | Python, Ruby, shell, PowerShell, Perl, R, YAML, TOML, Dockerfile, Makefile, CMake, Terraform |
| `slash` | `// ...` | Go, Rust, Zig, Protocol Buffers, F#, Solidity, Sass, JSONC |
| `c` | `/* ... */` | C, C++, C#, Java, Kotlin, Scala, Swift, Dart, JavaScript, TypeScript, CSS, PHP |
| `html` | `<!-- ... -->` | HTML, Vue, Svelte, Markdown |
| `xml` | `<!-- ... -->` | XML, SVG, XAML, MSBuild project files |
| `dash` | `-- ...` | SQL, Lua, Haskell, Elm, Ada, VHDL |
| `lisp` | `;; ...` | Emacs Lisp, Common Lisp, Clojure, Scheme, Racket |
| `semicolon` | `; ...` | INI, assembly |
| `percent` | `% ...` | Erlang, TeX |
| `bang` | `! ...` | Fortran |
| `apostrophe` | `' ...` | Visual Basic |
| `quote` | `" ...` | Vim script |
| `batch` | `:: ...` | Windows batch files |
| `ocaml` | `(* ... *)` | OCaml |
| `jinja` | `{# ... #}` | Jinja, Twig, Nunjucks |

Files without an extension, such as `bin/deploy`, are recognized by their `#!` line.

Some extensions mean different things in different projects, for example `.m`
(Objective-C or MATLAB) and `.v` (Verilog or Coq). These are not guessed. Map them, or
any other type, with `--style`:

```console
commentator add --header-file HEADER.txt --style '*.m=percent' --style 'Jenkinsfile.*=c'
```

Patterns match the file name and ignore case. When several match, the last one wins.

If the header contains text that would end the comment early, such as `*/` in a
`/* */` comment, that file is reported as an error and left unchanged.

## Settings file

file-commentator looks for `.commentator.toml`, or a `[tool.commentator]` table in
`pyproject.toml`, in the current folder and then in each parent folder. The first one
found is used. `--config FILE` points to a file directly.

`.commentator.toml`:

```toml
header-file = "HEADER.txt"   # relative to this file; or: header = "..."
include = ["*.py", "*.js"]
exclude = ["tests/fixtures", "*.min.js"]
gitignore = true

[variables]
author = "Example Corp"

[styles]
"*.txt" = "hash"
```

In `pyproject.toml`, the same keys go under `[tool.commentator]`, with
`[tool.commentator.variables]` and `[tool.commentator.styles]`.

Command-line options take precedence. `--include` replaces the `include` setting,
`--exclude` adds to the `exclude` setting, and `--var` and `--style` add to or
override `variables` and `styles`.

## CI and pre-commit

In GitHub Actions, with the header and other options in a settings file:

```yaml
- uses: actions/setup-python@v6
  with:
    python-version: "3.13"
- run: pip install git+https://github.com/kristenkamouh/file-commentator.git
- run: commentator check
```

With [pre-commit](https://pre-commit.com), add this to `.pre-commit-config.yaml`. Use
the `commentator-add` hook to add missing headers on commit, or `commentator-check` to
only report them:

```yaml
repos:
  - repo: https://github.com/kristenkamouh/file-commentator
    rev: v2.0.0
    hooks:
      - id: commentator-add
```

## Safety

- Files are replaced in one step: the new contents go to a temporary file, which then
  takes the original's place. A file is never left half-written, even if the run is
  interrupted or the disk fills up.
- Only files whose contents change are written.
- Binary files, files that are not UTF-8, symbolic links, and files over 10 MB are
  never written.
- Line endings (LF or CRLF), a UTF-8 byte order mark, and the executable bit are kept.
- `--dry-run` and `--diff` show what would change before anything does.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Success. For `check`: every file has the header. |
| 1 | For `check`: some files need the header. For any command: some files failed. |
| 2 | Invalid options or settings. No file was changed. |
| 130 | Interrupted with Ctrl+C. |

## Development

```console
git clone https://github.com/kristenkamouh/file-commentator.git
cd file-commentator
python -m venv .venv
source .venv/bin/activate        # on Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e . --group dev
```

Run the checks that CI runs:

```console
pytest
ruff check .
ruff format --check .
mypy
```

The code is in `src/file_commentator`:

| Module | Contents |
| --- | --- |
| `cli.py` | Command-line options and the main entry point |
| `wizard.py` | Guided mode |
| `config.py` | Reading settings files |
| `files.py` | Finding files, and writing them safely |
| `languages.py` | Comment styles and the file types that use them |
| `preamble.py` | Lines that must stay above the header |
| `header.py` | Rendering, finding, adding, and removing the header in a file's text |
| `runner.py` | Processing files in parallel |
| `report.py` | Progress, results, and summaries |

## License

MIT. See [LICENSE](LICENSE).
