import codecs
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest
from conftest import read, write

from file_commentator import runner
from file_commentator.header import Header, Status
from file_commentator.languages import FileTypes
from file_commentator.runner import Job, process_file, run


@pytest.fixture
def job(header: Header) -> Job:
    return Job(header, FileTypes())


def test_adds_header_and_keeps_byte_order_mark(tmp_path: Path, job: Job) -> None:
    path = tmp_path / "a.py"
    path.write_bytes(codecs.BOM_UTF8 + b"x = 1\r\n")

    result = process_file(path, job)

    assert result.status is Status.ADDED
    assert path.read_bytes() == (
        codecs.BOM_UTF8
        + b"# Copyright 2026 Example Corp\r\n# SPDX-License-Identifier: MIT\r\n\r\nx = 1\r\n"
    )


def test_binary_files_are_skipped(tmp_path: Path, job: Job) -> None:
    path = tmp_path / "video.ts"  # also the TypeScript extension
    path.write_bytes(b"G\x00\x11\x10" * 100)

    assert process_file(path, job) == runner.Result(path, Status.SKIPPED, "binary file")
    assert path.read_bytes() == b"G\x00\x11\x10" * 100


def test_text_that_is_not_utf8_fails_and_is_left_alone(tmp_path: Path, job: Job) -> None:
    path = tmp_path / "latin1.py"
    path.write_bytes("café = 1\n".encode("latin-1"))

    result = process_file(path, job)

    assert result.status is Status.FAILED
    assert "not UTF-8" in result.detail
    assert path.read_bytes() == "café = 1\n".encode("latin-1")


def test_unsupported_types_are_skipped_without_reading(tmp_path: Path, job: Job) -> None:
    path = tmp_path / "logo.png"
    path.write_bytes(b"\x89PNG")

    assert process_file(path, job).detail == "unsupported file type"


def test_files_without_extension_are_recognized_by_shebang(tmp_path: Path, job: Job) -> None:
    script = tmp_path / "deploy"
    write(script, "#!/usr/bin/env bash\necho hi\n")
    plain = tmp_path / "LICENSE"
    write(plain, "MIT License\n")

    assert process_file(script, job).status is Status.ADDED
    assert read(script).startswith("#!/usr/bin/env bash\n# Copyright")
    assert process_file(plain, job).detail == "unsupported file type"


def test_large_files_are_skipped(tmp_path: Path, job: Job, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "MAX_FILE_SIZE", 10)
    path = tmp_path / "big.py"
    write(path, "x = 1\n" * 10)

    assert process_file(path, job).detail == "larger than 10 MB"


def test_symbolic_links_are_skipped(tmp_path: Path, job: Job) -> None:
    target = tmp_path / "real.py"
    write(target, "x = 1\n")
    link = tmp_path / "link.py"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("cannot create symbolic links here")

    assert process_file(link, job).detail == "symbolic link"
    assert read(target) == "x = 1\n"


def test_preview_does_not_write_and_can_show_a_diff(tmp_path: Path, job: Job) -> None:
    path = tmp_path / "a.py"
    write(path, "x = 1")
    preview = Job(job.header, job.types, write=False, diff=True)

    result = process_file(path, preview)

    assert result.status is Status.ADDED
    assert read(path) == "x = 1"
    assert "+# Copyright 2026 Example Corp\n" in result.diff
    assert result.diff.endswith(" x = 1\n\\ No newline at end of file\n")


def test_file_that_cannot_hold_a_header_fails(tmp_path: Path, job: Job) -> None:
    path = tmp_path / "page.php"
    write(path, "<html><?php echo 1; ?></html>\n")

    result = process_file(path, job)

    assert result.status is Status.FAILED
    assert "<?php" in result.detail


def test_run_keeps_order_and_reports_progress(tmp_path: Path, job: Job) -> None:
    paths = []
    for index in range(300):
        path = tmp_path / f"f{index:03}.py"
        write(path, f"x = {index}\n")
        paths.append(path)
    progress: list[int] = []

    results = run(paths, job, on_progress=lambda done, total: progress.append(done))

    assert [result.path for result in results] == paths
    assert all(result.status is Status.ADDED for result in results)
    assert progress == list(range(1, 301))


@pytest.mark.skipif(os.name == "nt", reason="POSIX permissions")
def test_unwritable_file_fails(tmp_path: Path, job: Job) -> None:
    folder = tmp_path / "locked"
    folder.mkdir()
    path = folder / "a.py"
    write(path, "x = 1\n")
    folder.chmod(0o500)
    try:
        result = process_file(path, job)
    finally:
        folder.chmod(0o700)

    assert result.status is Status.FAILED
    assert read(path) == "x = 1\n"


@pytest.mark.skipif(os.name == "nt", reason="sends SIGINT")
def test_ctrl_c_never_leaves_a_half_written_file(tmp_path: Path) -> None:
    original = "x = 1\n" * 2000
    for index in range(2000):
        write(tmp_path / f"f{index:04}.py", original)
    command = [sys.executable, "-m", "file_commentator", "add", str(tmp_path)]
    process = subprocess.Popen([*command, "--header", "Copyright Example", "-q"])

    time.sleep(0.5)
    process.send_signal(signal.SIGINT)
    process.wait(timeout=60)

    complete = "# Copyright Example\n\n" + original
    assert all(read(path) in (original, complete) for path in tmp_path.glob("*.py"))
    assert list(tmp_path.glob(".*.tmp")) == []
