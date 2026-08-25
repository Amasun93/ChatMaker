# 星核板独立 CLI 最小闭环验证

日期：2026-08-26  
平台：Windows x64  
板卡：用户已确认的 IDMC-0001 星核板 v4.2.2  
代表案例：`C:\Users\asus\Desktop\chatmaker-test\starcore-quake-station\starcore-quake-station.ino`

## 范围卡

- 必须改：让 ChatMaker 自己准备星核板 CLI、固定核心和必需库，并验证编译、上传和串口。
- 绝不改：不恢复 MCP，不删除 rc5，不发布 SkillHub，不修改暂停中的 ChatCAD，不把命令成功写成未观察的实体效果。
- 验收证据：隔离目录准备成功；代表案例不引用 Mind+ 安装路径完成编译；COM4 上传四段哈希通过并硬复位；115200 串口看到新版界面标记和连续加速度数据。

## 固定工具链

- Arduino CLI：`0.33.1`，Windows 64-bit ZIP SHA-256 `58e7474a5873dbd7cad811ed4193223497d90445a6312397a65c08156b6c96d3`。
- 板卡索引：`https://resource.mindplus.top/mindplus/package/package_mindplus_index.json`。
- 核心：`mindplus:esp32@0.0.1`，核心 ZIP SHA-256 `00b08da1ee9e42a08480868ec2f8ec5c5159f7f54c6dec3fe4ba05eaa41ef0db`。
- FQBN：`mindplus:esp32:mpython:FlashMode=dio,FlashFreq=80,UploadSpeed=1500000,DebugLevel=none`。
- 固定库：`DFRobot_Mindplus_MPython`、`DFRobot_Mindplus_NeoPixel`、`DFRobot_Mindplus_SSD1306`、`DFRobot_MPython_Font`、`DFRobot_Mindplus_ASCIIfont`、`DFRobot_Mindplus_CHfont`，均为 `1.0.0`，每个下载包在运行期按代码中的固定 SHA-256 校验。

“不依赖 Mind+ 应用”表示不要求安装或启动 Mind+ 桌面程序；编译仍使用 Mind+ 公开维护的 Arduino 核心和 mPython 库。

## 真实结果

`prepare-environment` 在 `C:\Users\asus\AppData\Local\ChatMaker\toolchains\starcore` 建立隔离环境并通过完整性检查。代表案例随后使用 `backend=chatmaker-managed-starcore` 编译成功：Flash 277,388 字节（21%），动态内存 17,876 字节（6%）；日志中的核心和六个库全部来自 ChatMaker 隔离目录，没有引用 `E:\Mind+` 或 `E:\Mind+2`。

COM4 仍是唯一非蓝牙可上传端口。用户此前已经确认板卡身份，上传内容与板上原有中文防闪地震预警站相同。上传四段均返回 `Hash of data verified`，随后 `Hard resetting via RTS pin`。

115200 串口看到：

```text
STARCORE_QUAKE_STATION_BOOT
CALIBRATION_COMPLETE:baseline=1047.5
STARCORE_QUAKE_STATION_READY
STARCORE_QUAKE_STATION_UI_V2_READY
QUAKE_DATA:{..."level":"STABLE","muted":false}
```

这证明独立链路生成的固件已在真实板上启动并持续读取加速度。此前用户确认中文 OLED、防闪、预警、蜂鸣器、A 键静音和 B 键校准均正常；本轮没有重新肉眼或听觉确认这些实体效果，因此不把本轮命令结果升级成新的实体效果证据。

## 已知边界

- 当前自动准备仅支持 Windows x64；macOS/Linux 继续使用已有兼容后端，直到各自下载物和实机路径完成验证。
- Arduino CLI 的旧串口诊断会把同一轮 ESP32 正常启动中的 `ets/rst/boot` 三行误标为 `restart_loop_suspected`；连续 `QUAKE_DATA` 证明本次不是重启循环，此诊断修正留给后续聚焦任务。
- 本轮未发布 GitHub Release 或 SkillHub 包。
