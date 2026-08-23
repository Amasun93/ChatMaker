# Beginner Issue feedback and knowledge contribution

Use this reference for two different outcomes:

1. **Problem report:** the beginner remains blocked after one focused troubleshooting pass, or evidence suggests a ChatMaker defect rather than an ordinary wiring or usage mistake.
2. **Successful knowledge contribution:** the project produced reusable evidence that the current catalog or Knowledge does not cover, such as a new module, a corrected API or pin fact, or a repeatable workaround.

Do not confuse these paths. A blocked attempt is not a successful recipe, and one unexplained success is not yet reliable knowledge.

## Invite without burdening the beginner

For a likely defect, start with: “这可能不是你操作错了，我可以帮你把问题整理给开发者。”

For a successful contribution, first finish the project report, then ask once: “这次我们跑通了一个知识库里还没有的新模块或新经验。要不要我帮你整理成一个 Issue？你确认后再提交。” Do not ask after ordinary projects that only used existing guidance, and do not repeat the invitation after the user declines.

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

## Draft the Issue

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

Show the finished title, body and proposed attachments to the user. Submit publicly only after the user explicitly confirms all three. If direct GitHub submission is unavailable, use the matching repository page:

- Successful knowledge contribution: `https://github.com/Amasun93/ChatMaker/issues/new?template=knowledge-contribution.yml`
- Problem report: `https://github.com/Amasun93/ChatMaker/issues/new`

The user can paste the same reviewed text there later.
