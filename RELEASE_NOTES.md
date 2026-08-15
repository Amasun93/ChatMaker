# ChatMaker v0.1.0-rc4

这是面向教师培训和入门黑客松试运行的第四个发布候选。它在 rc3 的 Nano、常用模块资料、串口诊断、ChatWeb 和可逆安装基础上，新增了独立的 Arduino Uno Rev3 工作流。

## 相对 rc3 的新增内容

- 新增 Arduino Uno Rev3 独立适配器，不复用 Nano 的板卡参数。
- Mind+ 1.x 使用 `arduino:avr:uno`，Mind+ 2.x 使用 `mindplus:avr:uno`。
- Uno 上传固定使用 115200；不会继承 Nano 的 57600 后回退 115200 策略。
- Codex 新增 `chatmaker-uno`，支持环境检查、端口判断、编译和安全自动上传。
- WorkBuddy 新增 5 个 Uno 工具，MCP 工具总数由 13 个增加到 18 个。
- 新增 Uno 板载灯 Blink 示例和专属配方，资料库达到 3 块板卡、12 种元器件和 12 个配方。
- 自动测试由 77 项增加到 84 项，覆盖 Uno 的独立 FQBN、固定上传速度、蓝牙端口拒绝、多端口停止和无硬件等待。

## 已验证

- 84 项自动测试、本地 doctor 和三套 Skill 校验通过。
- GitHub Actions 在 Uno 功能进入公开 `main` 后通过。
- Uno Blink 使用 Mind+ 2.x 和 `mindplus:avr:uno` 真实编译成功，生成独立 HEX。
- 编译占用 2008 / 32256 字节程序空间、204 / 2048 字节动态内存。
- Codex 的 `chatmaker-uno doctor/compile` 路径通过真实调用。
- WorkBuddy MCP 实际加载 18 个工具，`uno_doctor` 和 `uno_compile` 通过真实调用。
- 当前只检测到 6 个蓝牙串口；它们均被排除，没有被误当成 Uno。

## 仍需现场验证

- 当前没有连接有线 Uno，因此没有执行 Uno 固件烧录。
- Uno 的 `UNO_BLINK_READY` 串口标记、断电重启和板载 LED 闪烁仍未验证。
- Nano 的实机烧录、真实串口、断电重启和物理效果仍未验证。
- ESP32 DevKit V1、真实网页硬件通信和完全不依赖 Mind+ 的工具链仍属于后续工作。

这些限制是明确的证据边界，不会由编译成功、自动测试、目录记录或模拟页面替代。
