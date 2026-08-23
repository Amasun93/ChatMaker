# Beginner Issue feedback and knowledge contribution

Use this reference for two different outcomes:

1. **Problem report:** the beginner remains blocked after one focused troubleshooting pass, or evidence suggests a ChatMaker defect rather than an ordinary wiring or usage mistake.
2. **Successful knowledge contribution:** the project produced reusable evidence that the current catalog or Knowledge does not cover, such as a new module, a corrected API or pin fact, or a repeatable workaround.

Do not confuse these paths. A blocked attempt is not a successful recipe, and one unexplained success is not yet reliable knowledge.

## Invite without burdening the beginner

For a likely defect, start with: “这可能不是你操作错了，我可以帮你把问题整理给开发者。”

For a successful contribution, first finish the project report. Explain what an Issue is and why it helps before asking: “这次我们跑通了一个知识库里还没有的新模块或新经验。Issue 可以理解成一张给 ChatMaker 开发者的改进建议单：我会帮你把模块型号、最终跑通的方法和踩过的坑整理好，你不需要懂 GitHub。提交后，开发者可以把这段经验补进 Skill 和知识库，让以后使用的人少走弯路。你愿意让我先整理一份给你确认吗？确认后再公开提交。” Do not ask after ordinary projects that only used existing guidance, and do not repeat the invitation after the user declines.

If the user already wrote a retrospective, treat it as source material. Extract only reusable facts; keep observations, interpretations and still-unverified guesses separate. Never turn an unverified guess into shared knowledge.

## Collect the smallest useful evidence

For either path, collect only what another person needs to understand or reproduce it:

- what the user wanted to make;
- the exact board revision and module name, model or visible markings;
- ChatMaker version, operating system, AI host, toolchain and relevant library version;
- expected and actual behavior for a defect, or the knowledge gap for a contribution;
- the final working wiring, API, settings or procedure;
- the pitfall or failed route that others should avoid;
- the highest evidence state actually reached: generated, compiled, uploaded, page opened, serial/browser interaction observed, or physical effect confirmed;
- one short useful error excerpt and the smallest relevant file, photo or screenshot.

Do not ask the user to reconstruct data that was never observed. Remove account names, home-directory names, tokens, passwords, Wi-Fi credentials, private URLs, faces, student information and unrelated logs. Do not gather a whole machine report when one excerpt and one reproducer are enough.

## Draft the feedback

Use one of these clear titles:

```text
[问题] 板卡或模块 + 一句话现象
[知识贡献] 板卡或模块 + 已跑通的新经验
```

Draft the body in this beginner-readable shape:

```text
我做了什么：
使用的板卡、模块和环境：
知识库缺少或写错了什么：
最终跑通的方法：
踩过的坑：
已经验证到哪一步：
建议补充到知识库的内容：
附件：
```

For a blocked defect, replace “最终跑通的方法” with “怎样可以再次出现” and record that the physical effect is not verified. Do not turn compilation success into a claim that hardware worked.

Before choosing a destination, show the finished draft, proposed attachments and any optional contact email to the user. Remove secrets and personal information, then ask the user to confirm what will be sent. The contact field is `联系邮箱（可选）`; never make it required.

Use GitHub first when the user has an account and is willing to use it. Submit publicly only after the user explicitly confirms the title, body and attachments. If direct GitHub submission is unavailable, use the matching repository page:

- Successful knowledge contribution: `https://github.com/Amasun93/ChatMaker/issues/new?template=knowledge-contribution.yml`
- Problem report: `https://github.com/Amasun93/ChatMaker/issues/new`

The user can paste the same reviewed text there later.

If the user has no GitHub account or does not want to use GitHub, use the ChatMaker Feishu form. In a local ChatMaker installation, create a reviewable prefilled link with `chatmaker-feedback --request-json '<json>'`, using action `draft_url` and the evidence fields collected above. The runtime reads the destination from `CHATMAKER_FEEDBACK_FORM_URL`; do not hard-code a private form URL in the Skill or repository.

The Feishu form fields are:

- `反馈类型`
- `问题标题`
- `我做了什么`
- `板卡、模块和环境`
- `预期结果`
- `实际结果或知识缺口`
- `怎样可以再次出现或最终跑通`
- `已经验证到哪一步`
- `最小错误摘录`
- `联系邮箱（可选）`
- hidden routing fields `提交来源` and `处理状态`

Open the prefilled link for the user, let them check it, and let the user perform or explicitly confirm the final submission. Do not upload arbitrary attachments through this fallback. If the configured command or form is unavailable, preserve the reviewed draft and explain that the fallback inbox is not configured; do not invent an email address. A Feishu submission does not need to become a GitHub Issue. Maintainers can read open records with action `list`; that action is read-only and takes its app credentials, app token and table ID from environment variables.
