# 掌控板 3.0 独立 CLI 编译验证

日期：2026-08-26  
平台：Windows x64  
板卡目标：掌控板 3.0（`mpython-v3`，ESP32-S3）  
代表案例：`examples/chatduino/mpython-v3/chinese-status/chinese-status.ino`

## 范围卡

- 必须改：建立不依赖 Mind+ 桌面应用的环境准备、doctor、端口、安全编译上传入口，并真实编译一个中文彩屏案例。
- 绝不改：不回退到经典掌控板或星核板目标，不把编译结果写成未发生的实板上传、串口或彩屏效果。
- 验收证据：环境、源码、编译、上传、串口、断电重启和实体效果七门分开；本轮没有掌控板 3.0 实物，停在编译门。

## 官方来源和固定工具链

- Arduino CLI `0.33.1`：14,311,609 字节，SHA-256 `58e7474a5873dbd7cad811ed4193223497d90445a6312397a65c08156b6c96d3`；
- Labplus 官方索引：`https://labplus-cn.github.io/arduino-esp32/package_esp32_mpython_index_cn.json`；
- 核心 `mpython:esp32@3.0.0`：44,968,645 字节，SHA-256 `51262c2e6b456ef80695119d8d0104a8cef42d6574abcc3d15650b8d510e611d`；
- 编译目标：`mpython:esp32:labplus_mpython_v3`；
- 板卡库：核心自带 `DFRobot_Mindplus_mPython 3.0.0`。

Windows x64 的五个间接依赖也由官方索引锁定：

| 工具 | 版本 | 大小 | SHA-256 |
| --- | --- | ---: | --- |
| esp32-arduino-libs | idf-release_v5.1-442a798083 | 79,063,774 | `009cba97f4a165e91280080fbb0b44345694473186386b64d6192c782026061f` |
| xtensa-esp32s3-elf-gcc | esp-12.2.0_20230208 | 135,381,926 | `1d15ca65e3508388a86d8bed3048c46d07538f5bc88d3e4296f9c03152087cd1` |
| esptool_py | 4.6 | 6,638,480 | `c7c68cd1aa520cbfce488ff6a77818ece272272eb012831b9d9ab1280a7c393f` |
| mkspiffs | 0.2.3 | 249,809 | `b647f2c2efe6949819c85ea9404271b55c7c9c25bcb98d3b98a1d0ba771adf56` |
| mklittlefs | 3.0.0-gnu12-dc7f933 | 345,132 | `2e319077491f8e832e96eb4f2f7a70dd919333cee4b388c394e0e848d031d542` |

这些第三方工具由 ChatMaker 在用户本机从官方索引和官方发行地址安装到隔离目录，不作为 ChatMaker 源码的一部分重新打包。掌控板官方文档声明文档 CC0、硬件 CERN-OHL-S-2.0、项目软件 GPL-3.0-or-later；各间接工具仍遵循各自项目许可证。

## Windows 兼容修复

首次编译稳定复现 `bits/c++config.h: No such file or directory`。压缩包中存在目标头文件，编译器单独运行也能找到；加入 Labplus 3.0.0 配方的 SDK `-iprefix` 后错误可单独复现，证明该参数覆盖了 Windows 编译器自身的 C++ 目标前缀。

ChatMaker 在隔离核心旁写入 `platform.local.txt`，只补回 `xtensa-esp32s3-elf/no-rtti` 的系统头目录。该覆盖不修改官方压缩包、不复制头文件，也不要求用户改案例代码；聚焦测试先复现缺失覆盖，再验证环境准备会稳定生成它。

## 真实结果

`prepare-environment` 在 `C:\Users\asus\AppData\Local\ChatMaker\toolchains\mpython-v3` 安装并验证核心、板卡定义和 Windows 兼容覆盖，返回 `ready_for_compile=true`。

随后通过正式 `chatmaker-mpython-v3` 编译入口运行代表案例，退出码 0：

- 源码：486 字节，SHA-256 `68413caa73fd906fe183f54139976e9533436711708064604225fd6469001c11`；
- 程序使用：1,064,121 字节（33%）；
- 动态内存：39,076 字节（11%）；
- 应用 BIN：1,064,480 字节，SHA-256 `754b0f0649549d8467fe24c826ff8a9ad6cbd98403e7c57a533176ee56977f87`；
- 分区 BIN：3,072 字节，SHA-256 `b9ee441ba65f8bf3b5e750e6fe8a6a72873b8490c73a0576df5905db9c59cfe4`。

案例在 `setup()` 中只绘制一次“掌控板3.0 / ChatMaker就绪 / 等待创意项目”，循环中不清屏，避免明显闪烁。

## 证据门

| 证据门 | 状态 | 说明 |
| --- | --- | --- |
| 环境 | 已验证 | 固定版本的隔离工具链完整可用 |
| 源码 | 已验证 | 静态中文状态页已登记并记录哈希 |
| 编译 | 已验证 | 正式 ChatMaker 入口退出码 0，产物存在 |
| 上传 | 未验证 | 当前没有掌控板 3.0 实物，不向星辰板 COM8 写入 |
| 串口 | 未验证 | 未观察 `MPYTHON_V3_CHINESE_STATUS_READY` |
| 断电重启 | 未验证 | 没有可用实板 |
| 实体效果 | 未验证 | 未肉眼确认彩屏中文、颜色、方向和闪烁情况 |

因此本阶段完成的是独立环境与代表案例编译，不是掌控板 3.0 实板闭环。拿到实板后只补精确身份、唯一端口、安全上传、串口、物理断电重启和彩屏肉眼确认。
