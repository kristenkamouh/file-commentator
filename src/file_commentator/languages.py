"""Comment styles, and the file types that use each one."""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fnmatch import fnmatchcase
from pathlib import PurePosixPath

from file_commentator.preamble import Preamble


@dataclass(frozen=True)
class CommentStyle:
    """How plain text is turned into a comment.

    Every line gets ``prefix``. Block styles also put ``start`` and ``end`` on lines of
    their own around the text. ``forbidden`` lists text that would end the comment early.
    """

    name: str
    prefix: str
    start: str = ""
    end: str = ""
    forbidden: tuple[str, ...] = ()

    def render(self, lines: Sequence[str]) -> list[str]:
        """Turn lines of text into comment lines, with no trailing whitespace."""
        body = [(self.prefix + line).rstrip() for line in lines]
        return [self.start, *body, self.end] if self.start else body

    def sample(self) -> str:
        """A short example of the style, such as ``/* ... */``."""
        if self.start:
            return f"{self.start} ... {self.end.strip()}"
        return f"{self.prefix}..."


STYLES: dict[str, CommentStyle] = {
    style.name: style
    for style in (
        CommentStyle("hash", "# "),
        CommentStyle("slash", "// "),
        CommentStyle("dash", "-- "),
        CommentStyle("semicolon", "; "),
        CommentStyle("lisp", ";; "),
        CommentStyle("percent", "% "),
        CommentStyle("bang", "! "),
        CommentStyle("apostrophe", "' "),
        CommentStyle("quote", '" '),
        CommentStyle("batch", ":: "),
        CommentStyle("c", " * ", "/*", " */", ("*/",)),
        CommentStyle("html", "  ", "<!--", "-->", ("<!--", "-->", "--!>")),
        CommentStyle("xml", "  ", "<!--", "-->", ("--",)),
        CommentStyle("ocaml", " * ", "(*", " *)", ("(*", "*)", '"')),
        CommentStyle("jinja", "  ", "{#", "#}", ("#}",)),
    )
}


@dataclass(frozen=True)
class Language:
    """A file type: its name, its comment style, and the lines that must stay above a header."""

    name: str
    style: CommentStyle
    preamble: Preamble = Preamble.NONE


def _builtin(
    name: str, style: str, *patterns: str, preamble: Preamble = Preamble.NONE
) -> tuple[Language, tuple[str, ...]]:
    return Language(name, STYLES[style], preamble), patterns


# Patterns are matched against the file name only, ignoring case.
# Extensions with more than one common meaning (.m, .pl for Prolog, .v, .pp) are left out
# on purpose; map them with --style.
# fmt: off
BUILTIN_TYPES: tuple[tuple[Language, tuple[str, ...]], ...] = (
    _builtin(
        "Python", "hash", "*.py", "*.pyi", "*.pyw", "*.pyx", "*.pxd",
        preamble=Preamble.CODING,
    ),
    _builtin(
        "Ruby", "hash", "*.rb", "*.rake", "*.gemspec", "Gemfile", "Rakefile", "Vagrantfile",
        preamble=Preamble.CODING,
    ),
    _builtin(
        "Shell", "hash", "*.sh", "*.bash", "*.zsh", "*.ksh", "*.fish",
        ".bashrc", ".bash_profile", ".bash_aliases", ".zshrc", ".zprofile", ".profile",
    ),
    _builtin("Perl", "hash", "*.pl", "*.pm"),
    _builtin("PowerShell", "hash", "*.ps1", "*.psm1", "*.psd1"),
    _builtin("R", "hash", "*.r"),
    _builtin("Julia", "hash", "*.jl"),
    _builtin("Elixir", "hash", "*.ex", "*.exs"),
    _builtin("Nim", "hash", "*.nim"),
    _builtin("Crystal", "hash", "*.cr"),
    _builtin("Tcl", "hash", "*.tcl"),
    _builtin("AWK", "hash", "*.awk"),
    _builtin("Nix", "hash", "*.nix"),
    _builtin("GraphQL", "hash", "*.graphql", "*.gql"),
    _builtin("YAML", "hash", "*.yml", "*.yaml"),
    _builtin("TOML", "hash", "*.toml"),
    _builtin("Terraform", "hash", "*.tf", "*.tfvars", "*.hcl"),
    _builtin("Makefile", "hash", "Makefile", "GNUmakefile", "*.mk", "*.mak"),
    _builtin("CMake", "hash", "CMakeLists.txt", "*.cmake"),
    _builtin(
        "Dockerfile", "hash", "Dockerfile", "Dockerfile.*", "*.dockerfile",
        "Containerfile", "Containerfile.*",
        preamble=Preamble.DOCKER,
    ),
    _builtin(
        "Starlark", "hash", "BUILD", "BUILD.bazel", "WORKSPACE", "WORKSPACE.bazel",
        "MODULE.bazel", "*.bzl", "*.star",
    ),
    _builtin(
        "Config files", "hash", "*.conf", "*.cfg", "*.properties", "*.env", ".env", ".env.*",
        ".editorconfig", ".gitignore", ".gitattributes", ".dockerignore", ".npmignore",
        ".prettierignore", ".eslintignore", "requirements*.txt",
    ),
    _builtin("Go", "slash", "*.go"),
    _builtin("Rust", "slash", "*.rs"),
    _builtin("Zig", "slash", "*.zig"),
    _builtin("Protocol Buffers", "slash", "*.proto"),
    _builtin("Thrift", "slash", "*.thrift"),
    _builtin("Solidity", "slash", "*.sol"),
    _builtin("F#", "slash", "*.fs", "*.fsi", "*.fsx"),
    _builtin("SystemVerilog", "slash", "*.sv", "*.svh", "*.vh"),
    _builtin("JSON with comments", "slash", "*.jsonc", "*.json5"),
    _builtin("Sass", "slash", "*.sass"),
    _builtin(
        "C and C++", "c", "*.c", "*.h", "*.cc", "*.cpp", "*.cxx", "*.c++", "*.hh", "*.hpp",
        "*.hxx", "*.h++", "*.ino", "*.cu", "*.cuh",
    ),
    _builtin("C#", "c", "*.cs"),
    _builtin("Java", "c", "*.java"),
    _builtin("Kotlin", "c", "*.kt", "*.kts"),
    _builtin("Scala", "c", "*.scala", "*.sc"),
    _builtin("Groovy", "c", "*.groovy", "*.gradle", "Jenkinsfile"),
    _builtin("Swift", "c", "*.swift"),
    _builtin("Dart", "c", "*.dart"),
    _builtin("Objective-C++", "c", "*.mm"),
    _builtin("JavaScript", "c", "*.js", "*.mjs", "*.cjs", "*.jsx"),
    _builtin("TypeScript", "c", "*.ts", "*.mts", "*.cts", "*.tsx"),
    _builtin("CSS", "c", "*.css", "*.scss", "*.less", preamble=Preamble.CHARSET),
    _builtin("PHP", "c", "*.php", preamble=Preamble.PHP),
    _builtin("HTML", "html", "*.html", "*.htm", "*.vue", "*.svelte", preamble=Preamble.XML),
    _builtin("Markdown", "html", "*.md", "*.markdown", preamble=Preamble.FRONT_MATTER),
    _builtin(
        "XML", "xml", "*.xml", "*.xhtml", "*.xsd", "*.xsl", "*.xslt", "*.svg", "*.plist",
        "*.csproj", "*.vbproj", "*.fsproj", "*.props", "*.targets", "*.resx", "*.xaml", "*.wsdl",
        preamble=Preamble.XML,
    ),
    _builtin("SQL", "dash", "*.sql"),
    _builtin("Lua", "dash", "*.lua"),
    _builtin("Haskell", "dash", "*.hs"),
    _builtin("Elm", "dash", "*.elm"),
    _builtin("Ada", "dash", "*.adb", "*.ads"),
    _builtin("VHDL", "dash", "*.vhd", "*.vhdl"),
    _builtin(
        "Lisp and Clojure", "lisp", "*.el", "*.lisp", "*.lsp", "*.clj", "*.cljs", "*.cljc",
        "*.edn", "*.scm", "*.ss", "*.rkt",
    ),
    _builtin("INI", "semicolon", "*.ini"),
    _builtin("Assembly", "semicolon", "*.asm"),
    _builtin("Erlang", "percent", "*.erl", "*.hrl"),
    _builtin("TeX", "percent", "*.tex", "*.sty", "*.cls", "*.ltx"),
    _builtin("Fortran", "bang", "*.f90", "*.f95", "*.f03", "*.f08"),
    _builtin("Visual Basic", "apostrophe", "*.vb", "*.vbs", "*.bas"),
    _builtin("Vim script", "quote", "*.vim", ".vimrc"),
    _builtin("Batch", "batch", "*.bat", "*.cmd", preamble=Preamble.ECHO_OFF),
    _builtin("OCaml", "ocaml", "*.ml", "*.mli"),
    _builtin("Jinja and Twig", "jinja", "*.j2", "*.jinja", "*.jinja2", "*.twig", "*.njk"),
)
# fmt: on


def _has_wildcard(pattern: str) -> bool:
    return any(char in pattern for char in "*?[")


def _build_index() -> tuple[dict[str, Language], dict[str, Language], list[tuple[str, Language]]]:
    by_name: dict[str, Language] = {}
    by_extension: dict[str, Language] = {}
    by_pattern: list[tuple[str, Language]] = []
    for language, patterns in BUILTIN_TYPES:
        for pattern in (p.lower() for p in patterns):
            if not _has_wildcard(pattern):
                by_name[pattern] = language
            elif pattern.startswith("*.") and not _has_wildcard(pattern[1:]):
                by_extension[pattern[1:]] = language
            else:
                by_pattern.append((pattern, language))
    return by_name, by_extension, by_pattern


_BY_NAME, _BY_EXTENSION, _BY_PATTERN = _build_index()
_BY_LANGUAGE_NAME = {language.name: language for language, _ in BUILTIN_TYPES}


def builtin_language(filename: str) -> Language | None:
    """Look up a file name in the built-in table."""
    name = filename.lower()
    if name in _BY_NAME:
        return _BY_NAME[name]
    for pattern, language in _BY_PATTERN:
        if fnmatchcase(name, pattern):
            return language
    return _BY_EXTENSION.get(PurePosixPath(name).suffix)


class FileTypes:
    """Finds the language of a file. Patterns given by the user win over the built-in table."""

    def __init__(self, overrides: Mapping[str, str] | None = None) -> None:
        """``overrides`` maps file name patterns to style names. Later entries win."""
        self._overrides: list[tuple[str, CommentStyle]] = []
        for pattern, style_name in (overrides or {}).items():
            style = STYLES.get(style_name.strip().lower())
            if style is None:
                raise ValueError(
                    f"unknown comment style '{style_name}' for '{pattern}'. "
                    "Run 'commentator styles' to see the available styles"
                )
            self._overrides.insert(0, (pattern.strip().lower(), style))

    def for_name(self, filename: str) -> Language | None:
        """Return the language for a file name, or None if it is not supported."""
        builtin = builtin_language(filename)
        name = filename.lower()
        for pattern, style in self._overrides:
            if fnmatchcase(name, pattern):
                if builtin is None:
                    return Language(pattern, style)
                return Language(builtin.name, style, builtin.preamble)
        return builtin


# fmt: off
_INTERPRETERS = {
    "sh": "Shell", "bash": "Shell", "zsh": "Shell", "ksh": "Shell", "dash": "Shell",
    "ash": "Shell", "fish": "Shell", "python": "Python", "pypy": "Python", "ruby": "Ruby",
    "perl": "Perl", "php": "PHP", "lua": "Lua", "pwsh": "PowerShell", "node": "JavaScript",
    "nodejs": "JavaScript", "deno": "JavaScript", "bun": "JavaScript", "ts-node": "TypeScript",
    "tsx": "TypeScript", "rscript": "R", "julia": "Julia", "elixir": "Elixir", "tclsh": "Tcl",
    "wish": "Tcl", "awk": "AWK", "gawk": "AWK", "make": "Makefile",
}
# fmt: on


def language_from_shebang(first_line: str) -> Language | None:
    """Guess the language of a script from its ``#!`` line, such as ``#!/usr/bin/env python3``."""
    if not first_line.startswith("#!") or first_line.startswith("#!["):
        return None
    words = first_line[2:].split()
    if words and _program(words[0]) == "env":
        words = [word for word in words[1:] if not word.startswith("-") and "=" not in word]
    if not words:
        return None
    program = re.sub(r"[\d.]+$", "", _program(words[0]))
    return _BY_LANGUAGE_NAME.get(_INTERPRETERS.get(program, ""))


def _program(word: str) -> str:
    return re.split(r"[\\/]", word)[-1].lower().removesuffix(".exe")
