from __future__ import annotations

import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from chatmaker.feedback import (
    FeedbackDraft,
    FeedbackError,
    FeishuFeedbackClient,
    build_prefilled_form_url,
    execute_request,
    main,
)


class FeedbackFormUrlTests(unittest.TestCase):
    def test_builds_reviewable_feishu_url_with_hidden_routing_fields(self):
        draft = FeedbackDraft(
            report_type="问题",
            title="星核板 OLED 不显示中文",
            project="制作一个中文姓名牌",
            hardware_environment="星核板 v4.2.2；Mind+ 1.8；Windows 11",
            expected_behavior="OLED 显示中文姓名",
            actual_behavior_or_gap="英文正常，中文显示为空白",
            reproduction_or_working_method="烧录后打开串口，再观察 OLED",
            evidence_state="已上传固件或打开页面",
            error_excerpt="串口无报错",
            email="tester@example.com",
            source_host="Codex",
        )

        url = build_prefilled_form_url(
            "https://example.feishu.cn/share/base/form/shrExample",
            draft,
        )
        query = parse_qs(urlparse(url).query)

        self.assertEqual(query["prefill_反馈类型"], ["问题"])
        self.assertEqual(query["prefill_问题标题"], ["星核板 OLED 不显示中文"])
        self.assertEqual(query["prefill_实际结果或知识缺口"], ["英文正常，中文显示为空白"])
        self.assertEqual(query["prefill_联系邮箱（可选）"], ["tester@example.com"])
        self.assertEqual(query["prefill_提交来源"], ["Codex"])
        self.assertEqual(query["hide_提交来源"], ["1"])
        self.assertEqual(query["prefill_处理状态"], ["新提交"])
        self.assertEqual(query["hide_处理状态"], ["1"])

    def test_rejects_non_feishu_form_urls(self):
        draft = FeedbackDraft(
            report_type="问题",
            title="标题",
            project="项目",
            hardware_environment="环境",
            expected_behavior="预期",
            actual_behavior_or_gap="实际",
            reproduction_or_working_method="步骤",
            evidence_state="只生成了源码或文件",
            source_host="WorkBuddy",
        )

        with self.assertRaisesRegex(FeedbackError, "Feishu"):
            build_prefilled_form_url("https://example.com/form", draft)


class FeishuFeedbackClientTests(unittest.TestCase):
    def test_lists_every_record_across_pages_using_read_only_requests(self):
        calls: list[tuple[str, str, dict[str, str], dict[str, str] | None]] = []

        def request_json(method, url, headers, body=None):
            calls.append((method, url, headers, body))
            if url.endswith("/tenant_access_token/internal"):
                return {"code": 0, "tenant_access_token": "token", "expire": 7200}
            if "page_token=next-page" in url:
                return {
                    "code": 0,
                    "data": {
                        "items": [{"record_id": "rec2", "fields": {"处理状态": "待复现"}}],
                        "has_more": False,
                    },
                }
            return {
                "code": 0,
                "data": {
                    "items": [{"record_id": "rec1", "fields": {"处理状态": "新提交"}}],
                    "has_more": True,
                    "page_token": "next-page",
                },
            }

        client = FeishuFeedbackClient(
            app_id="app-id",
            app_secret="app-secret",
            app_token="base-token",
            table_id="table-id",
            request_json=request_json,
        )

        records = client.list_records()

        self.assertEqual([item["record_id"] for item in records], ["rec1", "rec2"])
        self.assertEqual([call[0] for call in calls], ["POST", "GET", "GET"])
        self.assertEqual(calls[1][2]["Authorization"], "Bearer token")
        self.assertIn("page_size=500", calls[1][1])


class FeedbackRequestTests(unittest.TestCase):
    def test_draft_url_uses_form_url_from_environment(self):
        result = execute_request(
            {
                "action": "draft_url",
                "report_type": "问题",
                "title": "网页预览打不开",
                "project": "制作互动课件",
                "hardware_environment": "Windows 11；Codex",
                "expected_behavior": "打开本地预览",
                "actual_behavior_or_gap": "浏览器显示空白",
                "reproduction_or_working_method": "运行预览后打开链接",
                "evidence_state": "只生成了源码或文件",
                "source_host": "Codex",
            },
            environ={
                "CHATMAKER_FEEDBACK_FORM_URL": (
                    "https://example.feishu.cn/share/base/form/shrExample"
                )
            },
        )

        self.assertTrue(result["success"])
        self.assertIn("prefill_%E9%97%AE%E9%A2%98%E6%A0%87%E9%A2%98", result["url"])
        self.assertEqual(result["review_required"], True)

    def test_list_filters_actionable_statuses_without_writing(self):
        class FakeClient:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            def list_records(self):
                return [
                    {"record_id": "new", "fields": {"处理状态": "新提交"}},
                    {"record_id": "done", "fields": {"处理状态": "已完成"}},
                ]

        result = execute_request(
            {"action": "list", "statuses": ["新提交", "待复现", "处理中"]},
            environ={
                "FEISHU_APP_ID": "app-id",
                "FEISHU_APP_SECRET": "secret",
                "FEISHU_APP_TOKEN": "base-token",
                "FEISHU_TABLE_ID": "table-id",
            },
            client_factory=FakeClient,
        )

        self.assertTrue(result["success"])
        self.assertEqual([item["record_id"] for item in result["records"]], ["new"])
        self.assertNotIn("secret", str(result))

    def test_cli_returns_json_error_when_configuration_is_missing(self):
        with patch("chatmaker.feedback.os.environ", {}), patch(
            "chatmaker.feedback.sys.stdout"
        ) as stdout:
            exit_code = main(["--request-json", '{"action":"list"}'])

        self.assertEqual(exit_code, 1)
        rendered = "".join(call.args[0] for call in stdout.write.call_args_list)
        self.assertIn("feedback_configuration_missing", rendered)


if __name__ == "__main__":
    unittest.main()
