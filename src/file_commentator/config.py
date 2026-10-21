"""Settings from .commentator.toml, or from [tool.commentator] in pyproject.toml."""

import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar

T = TypeVar("T")

CONFIG_NAME = ".commentator.toml"
_KEYS = ("header", "header-file", "include", "exclude", "styles", "variables", "gitignore")


class ConfigError(Exception):
    """A settings file is unreadable or has invalid values."""


@dataclass
class Config:
    """Settings read from a file. Command-line options take precedence over them."""

    header: str | None = None
    include: list[str] = field(default_factory=list)
    exclude: list[str] = field(default_factory=list)
    styles: dict[str, str] = field(default_factory=dict)
    variables: dict[str, str] = field(default_factory=dict)
    gitignore: bool = True


def find_config(start: Path) -> Path | None:
    """Look for a settings file in ``start`` and then its parent folders."""
    for folder in (start, *start.parents):
        own_file = folder / CONFIG_NAME
        if own_file.is_file():
            return own_file
        pyproject = folder / "pyproject.toml"
        if pyproject.is_file() and "commentator" in _read_toml(pyproject).get("tool", {}):
            return pyproject
    return None


def load_config(path: Path) -> Config:
    """Read and check a settings file. A header file is read relative to the settings file."""
    data: Any = _read_toml(path)
    if path.name == "pyproject.toml":
        data = data.get("tool", {}).get("commentator", {})
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: [tool.commentator] must be a table")
    for key in data:
        if key not in _KEYS:
            raise ConfigError(
                f"{path}: unknown setting '{key}'. Valid settings are: {', '.join(_KEYS)}"
            )
    if "header" in data and "header-file" in data:
        raise ConfigError(f"{path}: set either 'header' or 'header-file', not both")

    config = Config()
    if "header" in data:
        config.header = _check(path, "header", data["header"], str, "a string")
    if "header-file" in data:
        header_file = _check(path, "header-file", data["header-file"], str, "a string")
        config.header = read_text(path.parent / header_file)
    config.include = _string_list(path, "include", data.get("include", []))
    config.exclude = _string_list(path, "exclude", data.get("exclude", []))
    config.styles = _string_table(path, "styles", data.get("styles", {}))
    config.variables = _string_table(path, "variables", data.get("variables", {}))
    config.gitignore = _check(path, "gitignore", data.get("gitignore", True), bool, "true or false")
    return config


def read_text(path: Path) -> str:
    """Read a UTF-8 text file, such as a header file."""
    try:
        return path.read_text(encoding="utf-8-sig")
    except OSError as error:
        raise ConfigError(f"cannot read {path}: {error.strerror or error}") from None
    except UnicodeDecodeError:
        raise ConfigError(f"cannot read {path}: it is not UTF-8 text") from None


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as stream:
            return tomllib.load(stream)
    except OSError as error:
        raise ConfigError(f"cannot read {path}: {error.strerror or error}") from None
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"{path} is not valid TOML: {error}") from None


def _check(path: Path, key: str, value: object, kind: type[T], description: str) -> T:
    if not isinstance(value, kind):
        raise ConfigError(f"{path}: '{key}' must be {description}")
    return value


def _string_list(path: Path, key: str, value: object) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ConfigError(f"{path}: '{key}' must be a list of strings")
    return list(value)


def _string_table(path: Path, key: str, value: object) -> dict[str, str]:
    if not isinstance(value, dict) or not all(isinstance(item, str) for item in value.values()):
        raise ConfigError(f"{path}: '{key}' must be a table of strings")
    return dict(value)
