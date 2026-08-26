# ChatMaker 0.2.0-beta.1 有什么新变化？

这是一份给普通老师、学生和体验者看的简短更新说明。

## 这次最重要的变化

- **ChatMaker 更精简了**：只保留一个 ChatMaker 入口，ChatDuino、ChatWeb 和 ChatCAD 在内部配合，不再要求额外配置旧 MCP。
- **星核板不用先安装 Mind+ 了**：在 Windows x64 上，ChatMaker 可以自己准备环境、编译、上传并读取串口。电脑里已有 Mind+ 1.8 或 2 也仍然可以使用。
- **证据说得更准确了**：编译、上传、串口和实物效果分开记录，不会再把“程序上传成功”写成“屏幕或蜂鸣器一定正常”。
- **版本更容易看懂了**：当前是 Beta 体验版；以后每次重要更新都会在这里用大白话说明。

## 你需要做什么？

如果你通过 GitHub 链接安装，请继续使用：

```text
https://github.com/Amasun93/ChatMaker
```

如果已经安装旧版，请让你使用的 AI 或 Skill 管理器从这个仓库重新更新。SkillHub 自动更新会在 P2 阶段继续打通。

## 接下来做什么？

先完成 SkillHub 分发和 Beta 反馈闭环，然后在 P3.1 补齐经典掌控板 V2.x，在 P3.2 调研并接入 micro:bit V2。具体安排见 [Beta 路线图](docs/roadmap.md)。
