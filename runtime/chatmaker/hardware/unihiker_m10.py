"""Static preflight checks for beginner UNIHIKER M10 Python projects."""

from __future__ import annotations

import argparse
import ast
import json
import re
from pathlib import Path
from typing import Any


MAX_SOURCE_BYTES = 1_000_000
SECRET_NAMES = re.compile(r"(?:api[_-]?key|secret|password|token)", re.IGNORECASE)
ABSOLUTE_PATH = re.compile(r"(?:[A-Za-z]:[\\/]|/Users/|/home/[^/]+/)")
DESKTOP_UI_MARKERS = ("cv2.imshow", "cv2.namedWindow", "cv2.setMouseCallback")
CREDENTIAL_GUIDANCE: dict[str, dict[str, Any]] = {
    "aliyun-dashscope": {
        "service": "阿里云百炼（DashScope / 通义千问）",
        "fields": ["aliyun.dashscope.api_key"],
        "replace_with": "账号所有者自己的阿里云百炼 API Key（普通 Key 通常以 sk- 开头）",
        "obtain_url": "https://bailian.console.aliyun.com/cn-beijing#/api-key",
        "docs_url": "https://help.aliyun.com/zh/model-studio/get-api-key",
        "notes": ["公开的 config.example.yaml 必须留空；真实值只放在不提交的 config.yaml 或环境变量中。"],
    },
    "aliyun-qwen-omni": {
        "service": "阿里云百炼 Qwen-Omni",
        "fields": ["aliyun.omni.api_key", "aliyun.omni.base_url"],
        "replace_with": "账号所有者自己的百炼 API Key，以及与该 Key 类型和业务空间匹配的端点",
        "obtain_url": "https://bailian.console.aliyun.com/cn-beijing#/api-key",
        "docs_url": "https://help.aliyun.com/zh/model-studio/get-api-key",
        "notes": [
            "普通 Key 与业务空间 Key 不能随意混用端点；从同一控制台确认并成对填写。",
            "M10 默认 Python 3.7；选择 SDK 或 HTTP 调用前先检查其 Python 版本要求。",
        ],
    },
    "volcengine-ark": {
        "service": "火山引擎方舟（豆包大模型）",
        "fields": ["huoshan.ark.api_key"],
        "replace_with": "账号所有者自己的火山方舟 API Key",
        "obtain_url": "https://console.volcengine.com/ark/region:cn-beijing/overview",
        "docs_url": None,
        "notes": ["公开的 config.example.yaml 必须留空；不要复用课程或内部项目 Key。"],
    },
    "volcengine-openspeech": {
        "service": "火山引擎语音技术（ASR / TTS）",
        "fields": ["huoshan.openspeech.app_key", "huoshan.openspeech.access_key"],
        "replace_with": "账号所有者在目标语音服务中创建的 App Key 和 Access Token",
        "obtain_url": "https://console.volcengine.com/speech/service/10038",
        "docs_url": None,
        "notes": ["App Key 与 Access Token 必须来自同一账号和已开通的服务。"],
    },
    "baidu-tts": {
        "service": "百度智能云语音合成",
        "fields": ["baidu.tts.app_id", "baidu.tts.api_key", "baidu.tts.secret_key"],
        "replace_with": "账号所有者在百度语音应用中创建的 App ID、API Key 和 Secret Key",
        "obtain_url": "https://console.bce.baidu.com/ai/#/ai/speech/app/list",
        "docs_url": None,
        "notes": ["三项凭据必须来自同一个语音应用。"],
    },
}


def _issue(level: str, code: str, message: str, path: Path | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"level": level, "code": code, "message": message}
    if path is not None:
        result["path"] = str(path)
    return result


def _entrypoint(project: Path) -> tuple[Path, Path]:
    root = project if project.is_dir() else project.parent
    main = project if project.is_file() else root / "main.py"
    if not main.exists() and project.is_dir():
        candidates = sorted(root.glob("*.py"))
        if len(candidates) == 1:
            main = candidates[0]
    return root, main


def _has_future_annotations(tree: ast.Module) -> bool:
    return any(
        isinstance(node, ast.ImportFrom)
        and node.module == "__future__"
        and any(alias.name == "annotations" for alias in node.names)
        for node in tree.body
    )


def _annotation_nodes(tree: ast.AST) -> list[ast.AST]:
    values: list[ast.AST] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign):
            values.append(node.annotation)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.returns is not None:
                values.append(node.returns)
            for argument in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs):
                if argument.annotation is not None:
                    values.append(argument.annotation)
            if node.args.vararg is not None and node.args.vararg.annotation is not None:
                values.append(node.args.vararg.annotation)
            if node.args.kwarg is not None and node.args.kwarg.annotation is not None:
                values.append(node.args.kwarg.annotation)
    return values


def _uses_runtime_incompatible_annotations(tree: ast.AST) -> bool:
    modern_bases = {"list", "dict", "tuple", "set", "type"}
    for annotation in _annotation_nodes(tree):
        for node in ast.walk(annotation):
            if (
                isinstance(node, ast.Subscript)
                and isinstance(node.value, ast.Name)
                and node.value.id in modern_bases
            ):
                return True
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
                return True
    return False


def _assigned_nonempty_secrets(tree: ast.AST) -> list[str]:
    names: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        value = node.value
        if not isinstance(value, ast.Constant) or not isinstance(value.value, str) or not value.value:
            continue
        for target in targets:
            if isinstance(target, ast.Name) and SECRET_NAMES.search(target.id):
                names.append(target.id)
    return sorted(set(names))


def _credential_providers_for_names(names: list[str]) -> list[str]:
    providers: set[str] = set()
    for name in names:
        upper = name.upper()
        if "OMNI" in upper:
            providers.add("aliyun-qwen-omni")
        elif "DASHSCOPE" in upper or "QWEN" in upper:
            providers.add("aliyun-dashscope")
        if "ARK" in upper:
            providers.add("volcengine-ark")
        if "OPENSPEECH" in upper or "BYTE_" in upper:
            providers.add("volcengine-openspeech")
        if "BAIDU" in upper:
            providers.add("baidu-tts")
    return sorted(providers)


def credential_help(provider: str) -> dict[str, Any]:
    guidance = CREDENTIAL_GUIDANCE.get(provider)
    if guidance is None:
        return {
            "success": False,
            "error": "credential_provider_not_supported",
            "provider": provider,
            "supported_providers": sorted(CREDENTIAL_GUIDANCE),
        }
    return {
        "success": True,
        "action": "credential_help",
        "provider": provider,
        **guidance,
        "public_example_value": "",
        "private_storage": "config.yaml or environment variable; exclude it from Git",
        "share_secret_with_chat": False,
        "shared_device_risk": (
            "A secret stored on an M10 can be read by someone with device access; "
            "classrooms should prefer a teacher-controlled proxy or a revocable low-limit key."
        ),
    }


def check_project(project: Path | str) -> dict[str, Any]:
    requested = Path(project).expanduser().resolve()
    root, main = _entrypoint(requested)
    issues: list[dict[str, Any]] = []

    if not main.is_file():
        issues.append(_issue("error", "main_missing", "找不到 main.py 或唯一 Python 入口", main))
        return {
            "success": False,
            "board_id": "unihiker-m10",
            "stage": "source_check_failed",
            "project": str(root),
            "issues": issues,
        }

    try:
        raw = main.read_bytes()
    except OSError as exc:
        issues.append(_issue("error", "main_unreadable", type(exc).__name__, main))
        return {
            "success": False,
            "board_id": "unihiker-m10",
            "stage": "source_check_failed",
            "project": str(root),
            "issues": issues,
        }
    if len(raw) > MAX_SOURCE_BYTES:
        issues.append(_issue("error", "main_too_large", "入口文件超过 1 MB 检查上限", main))
        return {
            "success": False,
            "board_id": "unihiker-m10",
            "stage": "source_check_failed",
            "project": str(root),
            "issues": issues,
        }
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        issues.append(_issue("error", "main_not_utf8", "入口文件必须使用 UTF-8", main))
        return {
            "success": False,
            "board_id": "unihiker-m10",
            "stage": "source_check_failed",
            "project": str(root),
            "issues": issues,
        }

    try:
        tree = ast.parse(text, filename=str(main), feature_version=(3, 7))
    except SyntaxError as exc:
        issues.append(
            _issue(
                "error",
                "python37_syntax",
                f"不兼容 Python 3.7：{exc.msg}，第 {exc.lineno} 行",
                main,
            )
        )
        return {
            "success": False,
            "board_id": "unihiker-m10",
            "stage": "source_check_failed",
            "project": str(root),
            "main": str(main),
            "issues": issues,
        }

    future_annotations = _has_future_annotations(tree)
    if _uses_runtime_incompatible_annotations(tree) and not future_annotations:
        issues.append(
            _issue(
                "error",
                "python37_annotations",
                "检测到 list[str] 或 X | None 等新式注解；请改用 typing.List/Optional，或启用 postponed annotations",
                main,
            )
        )

    secrets = _assigned_nonempty_secrets(tree)
    credential_guidance = [
        credential_help(provider)
        for provider in _credential_providers_for_names(secrets)
    ]
    if secrets:
        message = (
            "疑似写死密钥："
            + ", ".join(secrets)
            + "。公开代码应留空；请把内部值替换为账号所有者自己的凭据，并只存入不提交的 config.yaml 或环境变量"
        )
        issues.append(_issue("error", "embedded_secret", message, main))
    if ABSOLUTE_PATH.search(text):
        issues.append(
            _issue("warning", "absolute_path", "发现电脑相关绝对路径；资源应相对 __file__ 定位", main)
        )

    desktop = [marker for marker in DESKTOP_UI_MARKERS if marker in text]
    if desktop:
        issues.append(
            _issue(
                "warning",
                "desktop_ui",
                "检测到普通桌面 OpenCV 窗口；M10 独立运行应确认 240×320 全屏、触摸/板载按键或 headless 交互",
                main,
            )
        )
    if "VideoCapture" in text and ".release(" not in text:
        issues.append(_issue("error", "camera_not_released", "使用摄像头但未检测到 release()", main))
    if not (root / "requirements.txt").is_file():
        issues.append(
            _issue("warning", "requirements_missing", "缺少 requirements.txt；请记录项目额外依赖", root)
        )

    success = not any(item["level"] == "error" for item in issues)
    return {
        "success": success,
        "board_id": "unihiker-m10",
        "stage": "source_checked" if success else "source_check_failed",
        "project": str(root),
        "main": str(main),
        "python37_syntax": "verified",
        "desktop_ui_detected": bool(desktop),
        "board_execution": "unverified",
        "physical_effect": "unverified",
        "credential_help": credential_guidance,
        "issues": issues,
    }


def execute_request(request: Any) -> dict[str, Any]:
    if not isinstance(request, dict):
        return {"success": False, "error": "invalid_request", "detail": "request must be an object"}
    action = request.get("action")
    allowed = {"action", "project"} if action == "check_project" else {"action", "provider"}
    if set(request) - allowed:
        return {"success": False, "error": "invalid_request", "detail": "unsupported fields"}
    if action == "credential_help":
        provider = request.get("provider")
        if not isinstance(provider, str) or not provider.strip():
            return {"success": False, "error": "invalid_request", "detail": "provider must be a string"}
        return credential_help(provider)
    if action != "check_project":
        return {"success": False, "error": "unknown_action", "action": action}
    project = request.get("project")
    if not isinstance(project, str) or not project.strip():
        return {"success": False, "error": "invalid_request", "detail": "project must be a path string"}
    return check_project(project)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request-json", required=True)
    args = parser.parse_args(argv)
    try:
        request = json.loads(args.request_json)
        result = execute_request(request)
    except (json.JSONDecodeError, OSError, ValueError) as exc:
        result = {
            "success": False,
            "error": "unihiker_request_failed",
            "detail": f"{type(exc).__name__}: {exc}",
        }
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["check_project", "credential_help", "execute_request", "main"]
