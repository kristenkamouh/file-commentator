# Changelog

## 2.0.0

A rewrite. The single script is now an installable command, `commentator`, with
the same purpose: putting a header comment at the top of many files at once.

### Added

- `add`, `check`, and `remove` commands, plus `styles` to list file types.
- The header is written once as plain text and wrapped in the right comment syntax
  for each of 65 file types. Other types can be mapped with `--style`.
- Headers are placed after lines that must come first: `#!` lines, encoding
  declarations, `<?xml ...?>`, `<!DOCTYPE>`, `<?php`, CSS `@charset`, Dockerfile
  parser directives, Markdown front matter, and `@echo off`.
- `{year}` and `{filename}` placeholders, and custom ones with `--var`.
- `--update` to refresh existing headers, for example after the year changes.
- `--dry-run` and `--diff` to preview changes.
- `check` exits with code 1 when files are missing the header, for CI and pre-commit.
- Settings in `.commentator.toml` or `[tool.commentator]` in `pyproject.toml`.
- `.gitignore` is respected inside git repositories.
- Guided mode when run without arguments in a terminal.
- Pre-commit hooks, tests on Windows, macOS, and Linux, and type checking.

### Fixed

- Binary files (images, archives, executables) were rewritten and corrupted when no
  extension filter was given. They are now detected and skipped.
- Text that was not UTF-8 was silently damaged. Such files are now left unchanged and
  reported.
- The same `/* */` block was written into every file type, breaking Python, shell,
  YAML, and many others.
- Headers were inserted above `#!` lines and XML declarations, breaking those files.
- Line endings were converted (LF to CRLF on Windows), changing every line of every
  file in version control. Line endings, byte order marks, and file permissions are
  now kept.
- Interrupting the tool could leave a file half-written. Files are now replaced in a
  single step.
- Virtual environments and build folders (`.venv`, `venv`, `dist`, `build`, `target`)
  were processed.
- The progress bar could pass 100%, and large files were counted as "already had
  comment".
- Uppercase extensions such as `.PY` never matched.
- Blank lines inside a custom comment were dropped.
- A broken symbolic link stopped the whole run.
- Errors were counted but never shown. Each failure is now printed with its reason.
- Output crashed on Windows when redirected to a file, because of non-ASCII
  characters in the banner.

### Changed

- About 7 times faster: 5,000 files take about 9 seconds instead of 67 on Windows.
  The run no longer pauses after every file, scans the folder once, and processes
  files in parallel.
- Output is plain text with no emojis, and only a summary unless `-v` is given.

### Removed

- The default "test comment". A header must now be given.
