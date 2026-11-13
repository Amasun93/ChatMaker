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
from chatmaker.installers.locks import exclusive_file, rename_directory
from chatmaker.progress import emit
from . import arduino_toolchain as arduino


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
            "id": "arduino-downloads",
            "kind": "official_fallback",
            "url": "https://downloads.arduino.cc/arduino-cli/arduino-cli_0.33.1_Windows_64bit.zip",
        },
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
    "destination": f"data/packages/mindplus/hardware/esp32/{CORE_VERSION}",
    "packager": "mindplus",
    "strip_root": True,
    "sources": [
        {
            "id": "mindplus-cn",
            "kind": "domestic_official",
            "url": "https://resource.mindplus.top/mindplus/package/esp32/esp32-0.0.1.zip",
        }
    ],
}
# The three tools in Mind+'s official 0.0.1 package index for Windows x64.
CORE_TOOLS = {
    "xtensa-esp32-elf-gcc": ("5.2.0", "xtensa-esp32-elf-gcc-5.2.0-win64.zip", 73478484,
                            "b857c524946a55116fe5c009d47f0c19d624b4c10f5b066b6a78c703afdab40b"),
    "esptool_py": ("2.8", "esptool-2.8-windows.zip", 6037164,
                   "d32d52676d8fb010e4b6cc5dbf1a9124e783392c3d94845f430bf6394d4ae645"),
    "gen_esp32part_py": ("0.0.1", "gen_esp32part-0.0.1-windows.zip", 5458028,
                         "a1291f3eec8fb25f4016db3eb0e74ff5163a0328c962fcc437b7fcf3bc35ceef"),
}
BUILTIN_TOOLS = ('ctags', 'serial-discovery', 'mdns-discovery', 'serial-monitor', 'dfu-discovery')
FONT_DEVICE_ARTIFACT = {
    "filename": "dev-DFRobot-handpyEsp32@0.0.2.zip",
    "url": "https://resource.mindplus.top/mindplus/upload/devices/dev-DFRobot-handpyEsp32@0.0.2.zip",
    "size": 710058,
    "sha256": "ba72614c6b890fa2500b50d6a40a2f71fba9156b61ce72e2a12443ca77230cdd",
    "source_id": "mindplus-cn-device-package",
    "source_kind": "domestic_official",
    "sources": [
        {
            "id": "mindplus-cn-device-package",
            "kind": "domestic_official",
            "url": "https://resource.mindplus.top/mindplus/upload/devices/dev-DFRobot-handpyEsp32@0.0.2.zip",
        }
    ],
    "font_filename": "Noto_Sans_CJK_SC_Light16.xbf",
    "font_size": 1902314,
    "font_sha256": "75f647887f54441d569e17f1310520c322bdf7d2ea555ecededa45c9911bc5be",
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
        "firmware": selected / "firmware",
        "font": selected / "firmware" / str(FONT_DEVICE_ARTIFACT["font_filename"]),
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
        "tools": list(_core_tools().values()),
        "font_device_package": dict(FONT_DEVICE_ARTIFACT),
        "libraries": [dict(item) for item in LIBRARIES],
    }


def _core_tools() -> dict[str, dict]:
    artifacts = downloads.load_runtime_sources()['arduino_esp32']['artifacts']
    tools = {name: artifacts[name] for name in BUILTIN_TOOLS}
    for name, (version, filename, size, digest) in CORE_TOOLS.items():
        url = f'https://resource.mindplus.top/mindplus/package/esp32/{filename}'
        tools[name] = {'name': name, 'version': version, 'filename': filename, 'size': size, 'sha256': digest,
                       'destination': f'data/packages/mindplus/tools/{name}/{version}', 'packager': 'mindplus',
                       'strip_root': True, 'sources': [{'id': 'mindplus-cn', 'kind': 'domestic_official', 'url': url}],
                       'system': {'host': 'x86_64-mingw32', 'url': url, 'archiveFileName': filename,
                                  'checksum': 'SHA-256:' + digest, 'size': str(size)}}
    return tools


def _ready_files(paths: dict[str, Path]) -> bool:
    core = paths["data"] / "packages" / "mindplus" / "hardware" / "esp32" / CORE_VERSION / "boards.txt"
    libraries = paths["user"] / "libraries"
    required = [libraries / str(item["archive_root"]) / str(item["required_file"]) for item in LIBRARIES]
    try:
        font_ready = (
            paths["font"].is_file()
            and paths["font"].stat().st_size == FONT_DEVICE_ARTIFACT["font_size"]
            and _sha256(paths["font"]) == FONT_DEVICE_ARTIFACT["font_sha256"]
        )
    except OSError:
        font_ready = False
    return core.is_file() and all(path.is_file() for path in required) and font_ready


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
        or manifest.get("font_sha256") != FONT_DEVICE_ARTIFACT["font_sha256"]
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
        "font_asset": str(paths["font"]),
        "font_asset_verified": True,
    }


def _download_locked(item: dict[str, Any], destination: Path, *, timeout: int = 25) -> dict[str, Any]:
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
        rename_directory(extracted, target)
    except zipfile.BadZipFile as exc:
        raise ValueError(f"library_archive_invalid:{library['name']}") from exc
    finally:
        shutil.rmtree(temporary_root, ignore_errors=True)


def _install_font_device_archive(archive: Path, destination: Path) -> None:
    expected = f"firmware/{FONT_DEVICE_ARTIFACT['font_filename']}"
    try:
        with zipfile.ZipFile(archive) as bundle:
            names = {info.filename: info for info in bundle.infolist()}
            info = names.get(expected)
            if (
                info is None
                or Path(info.filename).is_absolute()
                or any(part in {"", ".", ".."} for part in Path(info.filename).parts)
                or (info.external_attr >> 16) & 0o170000 == 0o120000
                or info.file_size != FONT_DEVICE_ARTIFACT["font_size"]
            ):
                raise ValueError("font_device_archive_layout_invalid")
            payload = bundle.read(info)
    except zipfile.BadZipFile as exc:
        raise ValueError("font_device_archive_invalid") from exc
    if hashlib.sha256(payload).hexdigest() != FONT_DEVICE_ARTIFACT["font_sha256"]:
        raise ValueError("font_device_asset_identity_mismatch")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    temporary.write_bytes(payload)
    temporary.replace(destination)


def _write_config(paths: dict[str, Path]) -> None:
    for key in ("data", "downloads", "user"):
        paths[key].mkdir(parents=True, exist_ok=True)
    config = {
        "board_manager": {"additional_urls": []},
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


def _supported_host() -> bool:
    return os.name == "nt" and platform.machine().casefold() in {"amd64", "x86_64", "x64"}


def preview_environment() -> dict[str, Any]:
    root = default_root()
    return {
        "action": "prepare-environment",
        "status": "plan",
        "success": _supported_host(),
        "backend": BACKEND,
        "managed_root": str(root),
        "installation_performed": False,
        "ready_for_compile": managed_context(root) is not None,
        "toolchain_lock": toolchain_lock(),
        "stages": ["arduino-cli", "core", "libraries", "chinese-font"],
        "teacher_message": "星核板的独立工具链目前支持 Windows x64。",
    }


@downloads.download_session()
def prepare_environment_result(
    *,
    root: Path | None = None,
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
    if not _supported_host():
        return {**base, "success": False, "error": "managed_starcore_platform_not_yet_supported",
                "teacher_message": "星核板的独立工具链目前支持 Windows x64。"}
    try:
        with exclusive_file(paths["root"] / "prepare.lock"):
            ready = managed_context(paths["root"])
            if ready:
                return {**base, "success": True, "ready_for_compile": True, "environment": ready}
            return _install_environment(paths, base, downloader)
    except RuntimeError as exc:
        return {**base, "success": False, "error": str(exc),
                "teacher_message": "请等当前星核板工具准备任务结束，再复用同一个环境。"}
    except OSError as exc:
        return {**base, "success": False, "error": str(exc),
                "teacher_message": "无法写入星核板工具目录，请检查目录权限和磁盘空间。"}


def _install_environment(paths: dict[str, Path], base: dict[str, Any], downloader) -> dict[str, Any]:

    try:
        cli_archive = paths["downloads"] / str(ARDUINO_CLI_ARTIFACT["filename"])
        downloader(ARDUINO_CLI_ARTIFACT, cli_archive)
        _install_cli(cli_archive, paths["cli"])
        _write_config(paths)
    except (OSError, ValueError, downloads.DownloadError) as exc:
        return {
            **base,
            "success": False,
            "error": str(exc),
            "stage": "arduino-cli",
            "next_action": "place_verified_archive_in_managed_downloads_or_configure_mirror",
            "required_archive": str(paths["downloads"] / ARDUINO_CLI_ARTIFACT["filename"]),
            "teacher_message": (
                "Arduino CLI 的固定来源当前不可达。可把已核对大小和 SHA-256 的压缩包放到提示位置，"
                "或为学校的 HTTPS 镜像设置 CHATMAKER_DOWNLOAD_MIRROR_BASE 后重试。"
            ),
        }

    tools = _core_tools()
    artifacts = {'core': CORE_ARCHIVE, **tools}
    for name, item in artifacts.items():
        archive = paths['downloads'] / 'packages' / item['filename']
        emit('stage', stage='core', component=name, message='正在准备星核板编译与下载组件')
        try:
            if not arduino._artifact_ready(paths['root'], name, item):
                # Reuse the same Arduino helper archives across the board families.
                if item['packager'] == 'builtin' and not archive.is_file():
                    archive = arduino.archive_path(item)
                downloader(item, archive)
                arduino._install(paths['root'], name, item, archive)
        except (OSError, ValueError, downloads.DownloadError, zipfile.BadZipFile) as exc:
            return {**base, 'success': False, 'error': str(exc), 'stage': f'core:{name}',
                    'required_archive': str(archive), 'next_action': 'prepare-environment',
                    'teacher_message': '这个组件暂未取到。已保留缓存和进度，可用已校验的本地文件或学校镜像继续。'}

    platform_info = {'name': 'esp32', 'architecture': 'esp32', 'version': CORE_VERSION, 'category': 'ESP32',
                     'url': CORE_ARCHIVE['url'], 'archiveFileName': CORE_ARCHIVE['filename'],
                     'checksum': 'SHA-256:' + CORE_ARCHIVE['sha256'], 'size': str(CORE_ARCHIVE['size']),
                     'toolsDependencies': [{'packager': 'mindplus', 'name': name, 'version': tool['version']}
                                           for name, tool in tools.items() if tool['packager'] == 'mindplus']}
    index = arduino.offline_index({'platform': platform_info, 'artifacts': artifacts,
                                   'package_metadata': {'maintainer': 'mindplus', 'websiteURL': 'https://mindplus.cc/'}},
                                  list(artifacts))
    downloads._write_json(paths['data'] / 'package_index.json', index)
    downloads._write_json(paths['data'] / 'library_index.json', {'libraries': []})
    downloads._write_json(paths['root'] / CORE_ARCHIVE['destination'] / 'installed.json', index)

    for library in LIBRARIES:
        try:
            archive = paths["downloads"] / str(library["filename"])
            downloader(library, archive)
            _install_library_archive(archive, library, paths["user"])
        except (OSError, ValueError, downloads.DownloadError) as exc:
            return {**base, "success": False, "error": str(exc), "stage": f"library:{library['name']}"}

    try:
        font_archive = paths["downloads"] / str(FONT_DEVICE_ARTIFACT["filename"])
        downloader(FONT_DEVICE_ARTIFACT, font_archive)
        _install_font_device_archive(font_archive, paths["font"])
    except (OSError, ValueError, downloads.DownloadError) as exc:
        return {
            **base,
            "success": False,
            "error": str(exc),
            "stage": "chinese-font",
            "next_action": "place_verified_archive_in_managed_downloads_or_configure_mirror",
            "required_archive": str(font_archive),
        }

    if not _ready_files(paths):
        return {**base, "success": False, "error": "managed_starcore_files_incomplete", "stage": "verify"}
    manifest = {
        "schema_version": 1,
        "backend": BACKEND,
        "arduino_cli_version": ARDUINO_CLI_VERSION,
        "arduino_cli_executable_sha256": _sha256(paths["cli"]),
        "core": f"{CORE_ID}@{CORE_VERSION}",
        "font_sha256": FONT_DEVICE_ARTIFACT["font_sha256"],
        "libraries": [f"{item['name']}@{item['version']}" for item in LIBRARIES],
    }
    downloads._write_json(paths["manifest"], manifest)
    environment = managed_context(paths["root"])
    if not environment:
        return {**base, "success": False, "error": "managed_starcore_verification_failed", "stage": "verify"}
    return {
        **base,
        "success": True,
        "installation_performed": True,
        "ready_for_compile": True,
        "environment": environment,
        "executions": [],
    }
