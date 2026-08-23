from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Any, Callable, Mapping
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen


class FeedbackError(ValueError):
    pass


@dataclass(frozen=True)
class FeedbackDraft:
    report_type: str
    title: str
    project: str
    hardware_environment: str
    expected_behavior: str
    actual_behavior_or_gap: str
    reproduction_or_working_method: str
    evidence_state: str
    source_host: str
    error_excerpt: str = ""
    email: str = ""


def build_prefilled_form_url(form_url: str, draft: FeedbackDraft) -> str:
    parts = urlsplit(form_url)
    hostname = (parts.hostname or "").lower()
    if parts.scheme != "https" or not (
        hostname == "feishu.cn" or hostname.endswith(".feishu.cn")
    ):
        raise FeedbackError("Feedback form must use an HTTPS Feishu URL")

    values = {
        "反馈类型": draft.report_type,
        "问题标题": draft.title,
        "我做了什么": draft.project,
        "板卡、模块和环境": draft.hardware_environment,
        "预期结果": draft.expected_behavior,
        "实际结果或知识缺口": draft.actual_behavior_or_gap,
        "怎样可以再次出现或最终跑通": draft.reproduction_or_working_method,
        "已经验证到哪一步": draft.evidence_state,
        "最小错误摘录": draft.error_excerpt,
        "联系邮箱（可选）": draft.email,
        "提交来源": draft.source_host,
        "处理状态": "新提交",
    }
    query = list(parse_qsl(parts.query, keep_blank_values=True))
    query.extend(
        (f"prefill_{field_name}", value)
        for field_name, value in values.items()
        if value.strip()
    )
    query.extend((("hide_提交来源", "1"), ("hide_处理状态", "1")))
    result = urlunsplit(
        (parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment)
    )
    if len(result) > 16_000:
        raise FeedbackError("Feishu prefilled form URL exceeds 16,000 characters")
    return result


def _request_json(
    method: str,
    url: str,
    headers: dict[str, str],
    body: dict[str, str] | None = None,
) -> dict[str, Any]:
    payload = None if body is None else json.dumps(body).encode("utf-8")
    request = Request(url, data=payload, headers=headers, method=method)
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


class FeishuFeedbackClient:
    def __init__(
        self,
        *,
        app_id: str,
        app_secret: str,
        app_token: str,
        table_id: str,
        request_json: Callable[..., dict[str, Any]] = _request_json,
    ) -> None:
        self.app_id = app_id
        self.app_secret = app_secret
        self.app_token = app_token
        self.table_id = table_id
        self.request_json = request_json

    def list_records(self) -> list[dict[str, Any]]:
        token_response = self.request_json(
            "POST",
            "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
            {"Content-Type": "application/json; charset=utf-8"},
            {"app_id": self.app_id, "app_secret": self.app_secret},
        )
        if token_response.get("code") != 0 or not token_response.get(
            "tenant_access_token"
        ):
            raise FeedbackError(
                f"Feishu authentication failed: {token_response.get('msg', 'unknown error')}"
            )
        access_token = str(token_response["tenant_access_token"])
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=utf-8",
        }
        base_url = (
            "https://open.feishu.cn/open-apis/bitable/v1/apps/"
            f"{quote(self.app_token, safe='')}/tables/{quote(self.table_id, safe='')}/records"
        )
        records: list[dict[str, Any]] = []
        page_token: str | None = None
        while True:
            params: list[tuple[str, str]] = [
                ("page_size", "500"),
                ("automatic_fields", "true"),
            ]
            if page_token:
                params.append(("page_token", page_token))
            response = self.request_json(
                "GET", f"{base_url}?{urlencode(params)}", headers
            )
            if response.get("code") != 0:
                raise FeedbackError(
                    f"Feishu record read failed: {response.get('msg', 'unknown error')}"
                )
            data = response.get("data") or {}
            items = data.get("items") or []
            if not isinstance(items, list):
                raise FeedbackError("Feishu record response contained invalid items")
            records.extend(items)
            if not data.get("has_more"):
                return records
            page_token = data.get("page_token")
            if not page_token:
                raise FeedbackError("Feishu record response omitted the next page token")


_DRAFT_FIELDS = (
    "report_type",
    "title",
    "project",
    "hardware_environment",
    "expected_behavior",
    "actual_behavior_or_gap",
    "reproduction_or_working_method",
    "evidence_state",
    "source_host",
)


def _error(code: str, message: str) -> dict[str, Any]:
    return {"success": False, "error": {"code": code, "message": message}}


def _required_environment(
    environ: Mapping[str, str], names: tuple[str, ...]
) -> dict[str, str] | dict[str, Any]:
    missing = [name for name in names if not environ.get(name, "").strip()]
    if missing:
        return _error(
            "feedback_configuration_missing",
            "Missing environment variables: " + ", ".join(missing),
        )
    return {name: environ[name].strip() for name in names}


def execute_request(
    request: Any,
    *,
    environ: Mapping[str, str] | None = None,
    client_factory: Callable[..., FeishuFeedbackClient] = FeishuFeedbackClient,
) -> dict[str, Any]:
    """Create a reviewable form URL or read feedback records without mutation."""

    if not isinstance(request, dict):
        return _error("invalid_feedback_request", "Feedback request must be an object")
    action = request.get("action")
    env = os.environ if environ is None else environ
    try:
        if action == "draft_url":
            missing = [
                field
                for field in _DRAFT_FIELDS
                if not isinstance(request.get(field), str)
                or not request[field].strip()
            ]
            if missing:
                return _error(
                    "invalid_feedback_request",
                    "Missing non-empty text fields: " + ", ".join(missing),
                )
            config = _required_environment(env, ("CHATMAKER_FEEDBACK_FORM_URL",))
            if "success" in config:
                return config
            draft = FeedbackDraft(
                **{field: request[field].strip() for field in _DRAFT_FIELDS},
                error_excerpt=str(request.get("error_excerpt", "")).strip(),
                email=str(request.get("email", "")).strip(),
            )
            return {
                "success": True,
                "action": "draft_url",
                "url": build_prefilled_form_url(
                    config["CHATMAKER_FEEDBACK_FORM_URL"], draft
                ),
                "review_required": True,
            }

        if action == "list":
            config = _required_environment(
                env,
                (
                    "FEISHU_APP_ID",
                    "FEISHU_APP_SECRET",
                    "FEISHU_APP_TOKEN",
                    "FEISHU_TABLE_ID",
                ),
            )
            if "success" in config:
                return config
            statuses = request.get("statuses")
            if statuses is None:
                statuses = ["新提交", "待复现", "处理中"]
            if not isinstance(statuses, list) or not all(
                isinstance(status, str) and status.strip() for status in statuses
            ):
                return _error(
                    "invalid_feedback_request", "statuses must be a list of text values"
                )
            client = client_factory(
                app_id=config["FEISHU_APP_ID"],
                app_secret=config["FEISHU_APP_SECRET"],
                app_token=config["FEISHU_APP_TOKEN"],
                table_id=config["FEISHU_TABLE_ID"],
            )
            wanted = {status.strip() for status in statuses}
            records = [
                item
                for item in client.list_records()
                if isinstance(item, dict)
                and isinstance(item.get("fields"), dict)
                and item["fields"].get("处理状态") in wanted
            ]
            return {"success": True, "action": "list", "records": records}
    except FeedbackError as exc:
        return _error("feedback_operation_failed", str(exc))
    except (OSError, RuntimeError, ValueError) as exc:
        return _error(
            "feedback_operation_failed", f"Feedback operation failed: {type(exc).__name__}"
        )
    return _error("unknown_feedback_action", f"Unknown action: {action}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Draft a ChatMaker feedback form URL or read the feedback inbox."
    )
    parser.add_argument("--request-json", required=True, help="JSON object or '-' for stdin")
    args = parser.parse_args(argv)
    try:
        raw = sys.stdin.read() if args.request_json == "-" else args.request_json
        request = json.loads(raw)
    except (OSError, json.JSONDecodeError) as exc:
        result = _error(
            "invalid_feedback_request", f"Request JSON is invalid: {type(exc).__name__}"
        )
    else:
        result = execute_request(request)
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0 if result.get("success") else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "FeedbackDraft",
    "FeedbackError",
    "FeishuFeedbackClient",
    "build_prefilled_form_url",
    "execute_request",
    "main",
]
