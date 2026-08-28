"""ChatMaker-owned, hash-locked Starcore Arduino toolchain preparation.

The managed environment is deliberately separate from Mind+ and from the
user's normal Arduino directories.  It downloads an official Arduino CLI and
uses Mind+'s public board package and library archives without requiring the
Mind+ desktop application.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import tempfile
from typing import Any, Callable
import zipfile

from chatmaker.installers import downloads


BACKEND = "chatmaker-managed-starcore"
ARDUINO_CLI_VERSION = "0.33.1"
ARDUINO_CLI_ARTIFACT = {
    "filename": "arduino-cli_0.33.1_Windows_64bit.zip",
    "url": "https://github.com/arduino/arduino-cli/releases/download/0.33.1/arduino-cli_0.33.1_Windows_64bit.zip",
    "size": 14311609,
    "sha256": "58e7474a5873dbd7cad811ed4193223497d90445a6312397a65c08156b6c96d3",
    "source_id": "arduino-github",
    "source_kind": "official_fallback",
    "sources": [
        {
            "id": "arduino-github",
            "kind": "official_fallback",
            "url": "https://github.com/arduino/arduino-cli/releases/download/0.33.1/arduino-cli_0.33.1_Windows_64bit.zip",
        }
    ],
}
MINDPLUS_PACKAGE_INDEX_URL = "https://resource.mindplus.top/mindplus/package/package_mindplus_index.json"
CORE_ID = "mindplus:esp32"
CORE_VERSION = "0.0.1"
CORE_ARCHIVE = {
    "filename": "esp32-0.0.1.zip",
    "url": "https://resource.mindplus.top/mindplus/package/esp32/esp32-0.0.1.zip",
    "size": 35008313,
    "sha256": "00b08da1ee9e42a08480868ec2f8ec5c5159f7f54c6dec3fe4ba05eaa41ef0db",
    "source_id": "mindplus-cn",
    "source_kind": "domestic_official",
    "sources": [
        {
            "id": "mindplus-cn",
            "kind": "domestic_official",
            "url": "https://resource.mindplus.top/mindplus/package/esp32/esp32-0.0.1.zip",
        }
    ],
}
LIBRARIES = (
    {
        "name": "DFRobot_Mindplus_ASCIIfont", "archive_root": "DFRobot_ASCIIfont", "required_file": "DFRobot_ASCIIfont.h", "version": "1.0.0", "size": 1913,
        "sha256": "e3ed2df06ca624d9772cd05fafeff840f3bd716d89b4f4c6c87be33e0c347b0f",
    },
    {
        "name": "DFRobot_Mindplus_CHfont", "archive_root": "DFRobot_CHfont", "required_file": "DFRobot_CHfont.h", "version": "1.0.0", "size": 1461,
        "sha256": "67a2ee1b32d9f04ea99deb5eeb05895a43089fe507c9dadb55316000cdbf3fb1",
    },
    {
        "name": "DFRobot_MPython_Font", "archive_root": "MPython_Font", "required_file": "Unicode.h", "version": "1.0.0", "size": 94821,
        "sha256": "b786b07a5de519adcd9fd5ab2e023ea5ed5a5b4bccd21abf914eb7e80f3b225e",
    },
    {
        "name": "DFRobot_Mindplus_NeoPixel", "archive_root": "DFRobot_NeoPixel", "required_file": "DFRobot_NeoPixel.h", "version": "1.0.0", "size": 21009,
        "sha256": "e9ec15bef365d1726a553203ded3c78da81d9f787a6ffc4cb00be11906889912",
    },
    {
        "name": "DFRobot_Mindplus_SSD1306", "archive_root": "DFRobot_SSD1306", "required_file": "DFRobot_SSD1306_I2C.h", "version": "1.0.0", "size": 12888,
        "sha256": "8c6a618a609c99973a9a742dc3cae68860a6db42fa862f471986c65ab9f15c0c",
    },
    {
        "name": "DFRobot_Mindplus_MPython", "archive_root": "MPython", "required_file": "MPython.h", "version": "1.0.0", "size": 11636,
        "sha256": "e79a229a41688f9310dc6e978dd5616b568a3a9135986e56359642827a4e7e38",
    },
)
for _library in LIBRARIES:
    _library["filename"] = f"{_library['name']}-{_library['version']}.zip"
    _library["url"] = f"https://resource.mindplus.top/mindplus/arduino-libraries/{_library['filename']}"
    _library["source_id"] = "mindplus-cn"
    _library["source_kind"] = "domestic_official"
    _library["sources"] = [
        {
            "id": "mindplus-cn",
            "kind": "domestic_official",
            "url": _library["url"],
        }
    ]


def default_root() -> Path:
    override = os.environ.get("CHATMAKER_STARCORE_HOME")
    if override:
        return Path(override).expanduser().resolve()
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return (base / "ChatMaker" / "toolchains" / "starcore").resolve()


def _paths(root: Path | None = None) -> dict[str, Path]:
    selected = (root or default_root()).resolve()
    return {
        "root": selected,
        "cli": selected / "tool" / "arduino-cli.exe",
        "config": selected / "arduino-cli.yaml",
        "data": selected / "data",
        "downloads": selected / "downloads",
        "user": selected / "user",
        "manifest": selected / "manifest.json",
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def toolchain_lock() -> dict[str, Any]:
    return {
        "arduino_cli": {"version": ARDUINO_CLI_VERSION, **ARDUINO_CLI_ARTIFACT},
        "package_index": MINDPLUS_PACKAGE_INDEX_URL,
        "core": {"id": CORE_ID, "version": CORE_VERSION, **CORE_ARCHIVE},
        "libraries": [dict(item) for item in LIBRARIES],
    }


def _ready_files(paths: dict[str, Path]) -> bool:
    core = paths["data"] / "packages" / "mindplus" / "hardware" / "esp32" / CORE_VERSION / "boards.txt"
    libraries = paths["user"] / "libraries"
    required = [libraries / str(item["archive_root"]) / str(item["required_file"]) for item in LIBRARIES]
    return core.is_file() and all(path.is_file() for path in required)


def managed_context(root: Path | None = None) -> dict[str, Any] | None:
    paths = _paths(root)
    try:
        manifest = json.loads(paths["manifest"].read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if (
        manifest.get("schema_version") != 1
        or manifest.get("backend") != BACKEND
        or manifest.get("arduino_cli_version") != ARDUINO_CLI_VERSION
        or manifest.get("core") != f"{CORE_ID}@{CORE_VERSION}"
        or not paths["cli"].is_file()
        or not paths["config"].is_file()
        or _sha256(paths["cli"]) != manifest.get("arduino_cli_executable_sha256")
        or not _ready_files(paths)
    ):
        return None
    return {
        "backend": BACKEND,
        "root": str(paths["root"]),
        "cli": str(paths["cli"]),
        "config": str(paths["config"]),
        "version_family": f"arduino-cli-{ARDUINO_CLI_VERSION}",
        "toolchain_present": True,
        "managed_by_chatmaker": True,
    }


def _download_locked(item: dict[str, Any], destination: Path, *, timeout: int = 300) -> dict[str, Any]:
    return downloads.download_locked(
        downloads.legacy_artifact(item), destination, timeout=timeout
    ).to_dict()


def _install_cli(archive: Path, cli: Path) -> None:
    try:
        with zipfile.ZipFile(archive) as bundle:
            names = [name for name in bundle.namelist() if Path(name).name.casefold() == "arduino-cli.exe"]
            if len(names) != 1 or Path(names[0]).parts != ("arduino-cli.exe",):
                raise ValueError("arduino_cli_archive_layout_invalid")
            executable = bundle.read(names[0])
    except zipfile.BadZipFile as exc:
        raise ValueError("arduino_cli_archive_invalid") from exc
    cli.parent.mkdir(parents=True, exist_ok=True)
    temporary = cli.with_suffix(".exe.part")
    temporary.write_bytes(executable)
    temporary.replace(cli)


def _install_library_archive(archive: Path, library: dict[str, Any], user: Path) -> None:
    expected_root = str(library["archive_root"])
    libraries = user / "libraries"
    libraries.mkdir(parents=True, exist_ok=True)
    temporary_root = Path(tempfile.mkdtemp(prefix=f".{expected_root}-", dir=libraries))
    try:
        with zipfile.ZipFile(archive) as bundle:
            for info in bundle.infolist():
                parts = Path(info.filename).parts
                if (
                    not parts
                    or parts[0] != expected_root
                    or any(part in {"", ".", ".."} for part in parts)
                    or Path(info.filename).is_absolute()
                    or (info.external_attr >> 16) & 0o170000 == 0o120000
                ):
                    raise ValueError(f"library_archive_layout_invalid:{library['name']}")
            bundle.extractall(temporary_root)
        extracted = temporary_root / expected_root
        if not (extracted / str(library["required_file"])).is_file():
            raise ValueError(f"library_archive_incomplete:{library['name']}")
        target = libraries / expected_root
        if target.exists():
            shutil.rmtree(target)
        extracted.replace(target)
    except zipfile.BadZipFile as exc:
        raise ValueError(f"library_archive_invalid:{library['name']}") from exc
    finally:
        shutil.rmtree(temporary_root, ignore_errors=True)


def _write_config(paths: dict[str, Path]) -> None:
    for key in ("data", "downloads", "user"):
        paths[key].mkdir(parents=True, exist_ok=True)
    config = {
        "board_manager": {"additional_urls": [MINDPLUS_PACKAGE_INDEX_URL]},
        "directories": {
            "data": paths["data"].as_posix(),
            "downloads": paths["downloads"].as_posix(),
            "user": paths["user"].as_posix(),
        },
        "library": {"enable_unsafe_install": False},
        "metrics": {"enabled": False},
        "updater": {"enable_notification": False},
    }
    paths["config"].parent.mkdir(parents=True, exist_ok=True)
    paths["config"].write_text(json.dumps(config, ensure_ascii=True, indent=2) + "\n", encoding="ascii")


def _command(paths: dict[str, Path], *parts: str) -> list[str]:
    return [str(paths["cli"]), *parts, "--config-file", str(paths["config"]), "--no-color"]


def prepare_environment_result(
    *,
    root: Path | None = None,
    runner: Callable[..., dict[str, Any]],
    downloader: Callable[..., None] = _download_locked,
) -> dict[str, Any]:
    paths = _paths(root)
    base = {
        "action": "prepare-environment",
        "backend": BACKEND,
        "managed_root": str(paths["root"]),
        "toolchain_lock": toolchain_lock(),
        "installation_performed": False,
        "ready_for_compile": False,
    }
    ready = managed_context(paths["root"])
    if ready:
        return {**base, "success": True, "ready_for_compile": True, "environment": ready}
    if os.name != "nt" or platform.machine().casefold() not in {"amd64", "x86_64", "x64"}:
        return {**base, "success": False, "error": "managed_starcore_platform_not_yet_supported"}

    try:
        cli_archive = paths["downloads"] / str(ARDUINO_CLI_ARTIFACT["filename"])
        downloader(ARDUINO_CLI_ARTIFACT, cli_archive)
        _install_cli(cli_archive, paths["cli"])
        _write_config(paths)
    except (OSError, ValueError) as exc:
        return {**base, "success": False, "error": str(exc), "stage": "arduino-cli"}

    executions: list[dict[str, Any]] = []
    commands = [
        ("index", _command(paths, "core", "update-index"), 180),
        ("core", _command(paths, "core", "install", f"{CORE_ID}@{CORE_VERSION}", "--skip-post-install"), 900),
    ]
    for stage, command, timeout in commands:
        execution = runner(command, timeout=timeout)
        executions.append({"stage": stage, **execution})
        if execution.get("returncode") != 0:
            return {**base, "success": False, "error": f"managed_starcore_{stage}_failed", "stage": stage, "executions": executions}

    for library in LIBRARIES:
        try:
            archive = paths["downloads"] / str(library["filename"])
            downloader(library, archive)
            _install_library_archive(archive, library, paths["user"])
        except (OSError, ValueError) as exc:
            return {**base, "success": False, "error": str(exc), "stage": f"library:{library['name']}", "executions": executions}

    if not _ready_files(paths):
        return {**base, "success": False, "error": "managed_starcore_files_incomplete", "stage": "verify", "executions": executions}
    manifest = {
        "schema_version": 1,
        "backend": BACKEND,
        "arduino_cli_version": ARDUINO_CLI_VERSION,
        "arduino_cli_executable_sha256": _sha256(paths["cli"]),
        "core": f"{CORE_ID}@{CORE_VERSION}",
        "libraries": [f"{item['name']}@{item['version']}" for item in LIBRARIES],
    }
    paths["manifest"].write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="ascii")
    environment = managed_context(paths["root"])
    if not environment:
        return {**base, "success": False, "error": "managed_starcore_verification_failed", "stage": "verify", "executions": executions}
    return {
        **base,
        "success": True,
        "installation_performed": True,
        "ready_for_compile": True,
        "environment": environment,
        "executions": executions,
    }
