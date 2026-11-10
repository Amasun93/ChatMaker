# 独立课堂流程与微雪触屏板：软件验证记录

日期：2026-11-10。基线：`c6572c251c6b7421b5ce60fb58cbf527dd2d9f35`。

## 达到的阶段

本次在 `D:\Projects\ChatMaker` 的 `codex/esp32-s3-classroom-flow` 分支开发。新增连续执行入口，修正现行 Skill 和本地环境检查中强制寻找 Mind+ 的旧引导，并接入微雪 ESP32-S3-Touch-LCD-2.8。V1、V2 两版各两个示例均已由真实编译器生成固件。开发分支尚未发布。

**没有做实际烧录。** 用户实板版本仍未知；本机串口枚举为空。运行层测试、编译成功、写入成功、串口运行和屏幕/触摸效果分别记录，不相互替代。

## 课堂流程的变化

- 保存完整程序后，`chatmaker-hardware` 按准确板型调用对应适配器；已有工具直接复用，缺少时准备一次并继续原项目。
- 首轮支持此连续入口的适配器为星核、经典掌控板、掌控板 3.0、DOIT ESP32 DevKit V1、微雪触屏板。DOIT 仍沿用既有官方 CLI 发现/准备边界；不能据此声称所有板卡都具备零环境安装能力。
- Nano、Uno、星辰板保留原有兼容路径；micro:bit 保留 HEX 路径。缺少 Mind+ 不再作为已有独立路线的通用阻碍。
- 编译失败不会上传旧产物；缺少身份或有多个 USB 候选时不会猜测目标。上传、运行标记与实物效果独立返回。
- 厂商库只下载到本机隔离缓存，官方 ZIP 保持原样。本次没有把厂商源码、SDK、固件、缓存或本机配置提交到仓库。

## 固定的微雪配置

| 项目 | 值 |
| --- | --- |
| 准确板型 | ESP32-S3-Touch-LCD-2.8；不包含 2.8B、2.8C |
| Arduino CLI | 1.3.1，Windows x64 |
| Arduino-ESP32 | 3.3.11，官方索引 |
| 屏幕/图形库 | ST7789，厂商包 LVGL 8.3.10 |
| V1 触摸 | CST328 |
| V2 触摸 | CST3530 |
| Flash / PSRAM | 16 MB / OPI |
| 分区 | `app3M_fat9M_16MB` |
| USB | `USBMode=hwcdc,CDCOnBoot=cdc` |
| Flash 模式 | QIO |

完整 FQBN：

```text
esp32:esp32:esp32s3:FlashSize=16M,PartitionScheme=app3M_fat9M_16MB,PSRAM=opi,USBMode=hwcdc,CDCOnBoot=cdc,FlashMode=qio
```

直接检视 V2 ZIP 发现：包内虽有 CST3530 驱动，`Display_ST7789.cpp`、`LVGL_Driver.cpp` 仍调用 CST328。准备程序在本机副本中明确改为 `TOUCH2_Init`、`Touch2_Read_Data`、`Touch2_Get_XY` 和 CST3530 点数定义，排除 CST328 实现文件。V1 保持对应原始驱动。该变换有行为测试，并通过两版真实编译；触摸正确性仍待实板。

## 下载与恢复来源

| 文件 | SHA-256 |
| --- | --- |
| Arduino CLI 1.3.1 Windows 64bit ZIP | `cfece6f356fdc9ca003cc3f0a488470030719c8e0e7bfce5e42ac9410d87441f` |
| 微雪 V1 官方 Demo ZIP | `db9fb7ebb8ef773cc1218658c6a2e3d8adc5bb3883e360256a3acb16d073a773` |
| 微雪 V2 官方 Demo ZIP | `b09e8cdfb47212ea94a06ba02a11568dfb70dcc1ea040142067d08e374b29737` |
| V1 官方恢复固件 | `066e127edc6481db871025c4f8a68b4e9e41a9dcf2804b570a05ce4730699744` |
| V2 官方恢复固件 | `878fee6ed373e10f9101d7d256bdaa3d2973f81e59fc1f640b70c4a28ccc5517` |

两个 Demo ZIP 均含 `Firmware/ESP32-S3-Touch-LCD-2.8.bin`，分别保存到对应版本缓存，恢复写入地址按厂商说明为 `0x0`。这保留了官方恢复材料，**不等于备份了用户当前固件，也不等于已做恢复实测**。

厂商示例整体的独立再分发许可未确认，因此本次不重新发布这些源码或二进制。运行时只从固定官方地址下载，经大小和 SHA-256 校验后提取必要文件。

## 真实编译结果

每次编译使用全新的独立输出目录，只有退出码为 0 且新目录存在当前 `.ino.bin` 才算编译成功。以下为应用固件，不是可直接在 `0x0` 写入的合并恢复镜像；实际项目上传由 Arduino CLI 配合本次构建产物完成。

| 版本 | 示例 | 字节数 | 应用固件 SHA-256 |
| --- | --- | ---: | --- |
| V1 | 屏幕诊断 | 514000 | `42486316681968871844f04a3616b9f684d33ea06c74fef6eb8a6aa2a3c63bbc` |
| V1 | 课堂计时器 | 515216 | `268d4cb8968990c398cb1d5677e08775edc65d9de56d3b8580f62a19f5ae5240` |
| V2 | 屏幕诊断 | 511280 | `23999abdde49d1cdb8102b0525d0b079fd79058843ab8099e16b80d27f9ef5fb` |
| V2 | 课堂计时器 | 512464 | `d1f54b8014c1e343a6c7a4e85b2be6a8ef8863840f65dbb2af8488e5d0b82f4b` |

计时器为 60 秒，使用明确可读的 START / PAUSE / RESET 控件。两例每两秒重复运行标记，供 USB 复位后打开的串口观察器使用；目前未宣称具备通用中文字库。

两版准备完成后再次执行均返回 `installation_performed=false`。最终准备目录的全部驱动/库哈希与实际编译时使用的目录一致：V1 共 1690 个文件，V2 共 1691 个。额外混入的旧驱动、修改或缺失的已记录文件、丢失恢复材料都会使环境检查失败。已记录工具损坏时停下保留证据，不重新写一张“正常”凭据。

## 自动检查与本机边界

- Python 全量测试：最终复验进行中，完成后补记。
- Chromium 浏览器回归：5/5 通过，覆盖原有网页交互，不代表开发板验证。
- `runtime/doctor.py`：数据包、机械资料、四个 Skill 通过；10 板卡、35 元器件、33 配方、8 索引。
- `scripts/validate_skills.py`：四个 Skill 通过。
- 行为回归覆盖：环境复用、准备失败停止、旧适配器错误格式、无上传证据不报成功、同一设备重新枚举、未知版本/身份阻断、编译失败/无产物不上传、V2 驱动选择、缓存变更识别。

本机原有全量测试首次运行失败于测试环境：新建 venv 继承的是便携 Python 的基础 site-packages，不是外层 venv；依赖现已补齐到项目内的便携 Python。另一个旧发行安装用例的层层临时目录超过 Windows 路径限制。此用例改用短前缀及显式隔离安装根，并保留中文用户目录、签名检查、真实安装与本地检查；默认目录选择继续由既有 bootstrap 单元测试覆盖。复验使用仓库外较短的 `D:\Codex\workspace\work\cm` 临时目录，避免签名测试的临时密钥和 Skill 打包目标落在源码仓库内而被既有保护规则拒绝。没有修改系统长路径设置或全局 PATH；普通超长安装路径问题未在本轮修复。

可复验命令（仓库目录，PowerShell）：

```powershell
New-Item -ItemType Directory -Path D:\Codex\workspace\work\cm -Force | Out-Null
$env:TEMP = 'D:\Codex\workspace\work\cm'
$env:TMP = $env:TEMP
.\.chatmaker-runtime\venv\Scripts\python.exe -m unittest discover -s tests -v
npm.cmd run test:browser
.\.chatmaker-runtime\venv\Scripts\python.exe runtime/doctor.py
.\.chatmaker-runtime\venv\Scripts\python.exe scripts/validate_skills.py
```

WorkBuddy：发现本机用户数据目录，其中最近启动记录标为 5.9.3；这不是当前运行版本的证明。检查时没有 WorkBuddy/CodeBuddy 运行进程，也未在检查的常用 Skill 目录中定位到当前 ChatMaker 加载副本。本轮没有启动真实 WorkBuddy 项目会话或改写其配置，因此只证明仓库规则与本地 CLI 行为，**不能声称 WorkBuddy 的实际绕路问题已经现场消失**。

## 接板后的验收

1. 确认实物是准确的 2.8 型号及 V1/V2，保留当前固件需要时先做备份。
2. 使用数据 USB 接口，确认目标后先跑屏幕诊断，记录上传退出码、重新枚举的端口及重复运行标记。
3. 跑计时器，观察屏幕与 START / PAUSE / RESET 三个触控行为，再断电重启。
4. 在 WorkBuddy 中加载本地开发版本，完成一次描述需求到下载；修改一处效果，再次运行并检查是否复用工具、不要求安装 Mind+。

## 技术决定与保留边界

- 使用用户指定的独立 checkout 和现有功能分支，未另建第二份工作树；代价是并行编辑此目录时需要继续留意工作树状态。
- 连续入口与新板适配一起提交，避免出现已登记 CLI 但缺少适配器的中间版本；独立的发布步骤另行执行。
- 测试采用短的隔离安装根，避免测试目录层级掩盖本次功能结果；代价是本轮不能证明任意超长安装路径可用。
- 真实编译不替代实板与宿主验收；缺失的硬件和版本信息不进行猜测。

## 官方资料

- [微雪板卡说明](https://docs.waveshare.net/ESP32-S3-Touch-LCD-2.8/)
- [V1/V2 示例、固件与原理图](https://docs.waveshare.net/ESP32-S3-Touch-LCD-2.8/Resources-And-Documents/)
- [微雪 Arduino 使用说明](https://docs.waveshare.net/ESP32-S3-Touch-LCD-2.8/Arduino/)
- [Arduino CLI 1.3.1](https://github.com/arduino/arduino-cli/releases/tag/v1.3.1)
- [乐鑫官方 Arduino 平台索引](https://espressif.github.io/arduino-esp32/package_esp32_index.json)
