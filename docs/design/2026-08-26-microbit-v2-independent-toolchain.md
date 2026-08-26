# micro:bit V2 独立工具链调研与阶段设计

日期：2026-08-26

状态：官方一手资料核验完成，设计可讨论；本阶段未实现运行层、板卡包或自动下载

目标板：BBC micro:bit V2.x（nRF52833），V1 不在当前范围

## 范围卡

- 必须改：客观比较官方支持的生成、下载、烧录和串口路线，给出适合 ChatMaker 小白用户的 V2 优先方案与证据门。
- 绝不改：不复制星核板 Arduino 路线，不在本阶段引入完整 Node/C++ 构建栈，不把 U 盘复制成功写成程序启动或实体效果成功。
- 验收证据：官方来源、版本与许可证可追溯；下一实施阶段分别验证源码、HEX 生成、MICROBIT 写入、`FAIL.TXT`、重新枚举、115200 串口、断电重启和实体效果。

## 精确硬件与 USB 路线

micro:bit V2 的目标 MCU 是 nRF52833。V2.00 的 USB 接口 MCU 是 KL27，V2.2x 是 nRF52820；两者都运行 DAPLink，但接口固件版本不能互相替代。DAPLink 同时提供：

- MSC：名为 `MICROBIT` 的虚拟 U 盘，把写入的 HEX 流式烧录到目标 MCU；它不是普通存储盘。
- CDC：目标 MCU 到电脑的 USB 串口透传。
- HID/CMSIS-DAP：调试和高级烧录通道。
- WebUSB：浏览器直连、烧录和串口。

普通程序只能写入 `MICROBIT` 盘。`MAINTENANCE` 是接口固件维护模式，不能作为普通上传目标。烧录后必须检查 `FAIL.TXT`，等待设备重新枚举，再进入串口和实体证据门。

## 路线比较

| 路线 | 生成/编译 | 烧录 | 串口 | 依赖与风险 | 适合 ChatMaker |
| --- | --- | --- | --- | --- | --- |
| MicroPython + `microbit-fs` | 把 Python 文件与固定 MicroPython V2 运行时合成 HEX；这一步应叫“HEX 打包”，不冒充本地原生编译 | 首选复制到 `MICROBIT`；后续可选 WebUSB | DAPLink CDC，115200 8N1；也可进入 REPL | MIT；依赖小，API 贴近教育场景；运行时不是最新源码构建 | **默认第一层** |
| MakeCode / PXT | TypeScript/MakeCode Python 真正编译成 HEX，官方编辑器支持离线缓存 | `pxt deploy` 或写入 `MICROBIT` | `pxt console` 或 CDC/WebUSB | MIT；`pxt-core` 与目标包体积大，依赖 Node/npm，版本组合需整体锁定 | **第二层编译路线** |
| CODAL C/C++ | GNU Arm + CMake + Python 构建原生 C/C++，输出 `MICROBIT.hex` | 写入 `MICROBIT`，调试可接 pyOCD/OpenOCD | CODAL 串口或调试器 | MIT，但 Windows 工具链、依赖仓库和构建成本明显更高 | 高级扩展，不做首发 |
| pyOCD / CMSIS-DAP | 不负责编写普通教育项目 | 通过 HID/SWD 烧录和调试 | 调试通道，不替代普通 CDC 用户流 | Apache-2.0；目标包、探针选择和擦写能力带来更多误操作面 | 仅恢复/调试，不做默认上传 |
| 纯 DAPLink U 盘 | 不生成 HEX | 最简单、免驱、官方支持 | CDC 另开 | 必须已有可信 HEX；盘会在写入后弹出/重枚举 | 作为所有默认路线的上传层 |

## 推荐的两层方案

### 第一层：MicroPython V2 + DAPLink MSC + CDC

这是最适合 ChatMaker 第一版的独立链：

1. 固定官方 MicroPython V2 `2.1.1` HEX：1,239,726 字节，SHA-256 `5bd5d4584a5caae740a66d38f93651968569dd4b52f4bc132ebf3c6fdf3847ac`，MIT。
2. 固定 `@microbit/microbit-fs@0.10.0`：MIT；npm 完整性 `sha512-n6DEVqqaQAL/EDLyXh+1nsdRV16ePFqROeFeNlOoTS23eB8zF8qhA+IaNHRT07sy0zgCGg3YCZgP+zcCIRzP6A==`，解包约 300,772 字节。
3. ChatMaker 生成完整 `main.py`，先做 Python 语法与受支持 API 检查，再合成 V2 HEX。结果门命名为 `source_checked` 和 `hex_packaged`，不命名为 `code_compiled`。
4. 只把 HEX 写入唯一、身份匹配且处于 `MICROBIT` 模式的卷；拒绝 `MAINTENANCE`，多块设备必须选择。
5. 等待盘弹出并重新枚举，检查 `FAIL.TXT`；没有失败文件只能证明 DAPLink 未报告写入错误，仍不能证明程序启动。
6. 以 115200 8N1 打开对应 CDC 串口，匹配项目自带启动标记；再单独要求断电重启和实体效果确认。

这个选择不是因为 Python“功能最多”，而是因为它用官方、许可证清晰、体积小的运行时和打包库，能把第一版的本地依赖、误刷风险和小白认知负担压到最低。

### 第二层：MakeCode/PXT 编译

在第一层实板闭环稳定后，再加入需要真正本地编译的 TypeScript/MakeCode 项目：

- 当前官方目标 `pxt-microbit@9.1.1`（MIT，解包约 16,417,579 字节）。
- 配套 `pxt-core@13.0.1`（MIT，解包约 72,013,733 字节）与 `pxt-common-packages@14.0.2` 必须整体固定。
- 首次实施前要在干净 Windows x64 环境真实测量完整 npm 依赖大小、离线构建、目标缓存、输出 HEX、`pxt deploy` 和 `pxt console`；不能只按三个顶层包的体积估算。
- 仍复用同一个 DAPLink 设备识别、写入、`FAIL.TXT`、重新枚举和证据门，不另造上传协议。

## 不选 CODAL 或 pyOCD 作为首发的原因

CODAL V2 是官方运行时，稳定发行是适合原生 C/C++ 的正确路线，但官方样例要求 GNU Arm、Git、CMake 和 Python，Windows x64 的固定工具链、依赖仓库和构建体积明显大于本阶段主体。pyOCD 适合 CMSIS-DAP 调试、恢复和专业烧录，但普通 micro:bit 已有免驱 DAPLink MSC；把 pyOCD 放进默认路径会增加目标包、探针和擦写选择，收益不足以覆盖风险。

## 下一实施阶段的最小范围

只实现 MicroPython 第一层：

- 新增精确板卡 `microbit-v2`，记录 V2.00/V2.2x 接口 MCU 差异，但软件目标统一为 nRF52833；不加入 V1。
- 新增隔离下载锁、doctor、`package-hex`、卷识别、安全 `flash`、CDC `serial-read` 与一个 LED/串口代表案例。
- Windows 卷识别同时核对卷标 `MICROBIT`、`DETAILS.TXT` 和接口版本；不能仅凭盘符或文件夹名上传。
- 证据门：环境／源码检查／HEX 打包／写盘／`FAIL.TXT`／重新枚举／串口／断电重启／实体效果。
- 只运行 micro:bit 聚焦测试和一条 Knowledge 读取路径；MakeCode、CODAL、pyOCD 不在同一实现批次。

## 官方来源

- micro:bit Foundation DAPLink/USB interface：<https://tech.microbit.org/software/daplink-interface/>
- micro:bit Foundation MakeCode overview：<https://tech.microbit.org/software/makecode/>
- micro:bit Foundation MicroPython overview：<https://tech.microbit.org/software/micropython/>
- micro:bit MicroPython V2：<https://github.com/microbit-foundation/micropython-microbit-v2>
- micro:bit Python Editor V3 技术概览：<https://github.com/microbit-foundation/python-editor-v3/blob/main/docs/tech-overview.md>
- microbit-fs：<https://github.com/microbit-foundation/microbit-fs>
- MakeCode CLI：<https://makecode.com/cli>
- pxt-microbit：<https://github.com/microsoft/pxt-microbit>
- CODAL V2：<https://github.com/lancaster-university/codal-microbit-v2>
- micro:bit V2 CODAL samples：<https://github.com/lancaster-university/microbit-v2-samples>
- pyOCD：<https://github.com/pyocd/pyOCD>
