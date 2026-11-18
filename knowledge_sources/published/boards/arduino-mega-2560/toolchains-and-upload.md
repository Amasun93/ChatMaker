---
schema_version: "1.0"
kind: knowledge-page
stable_id: arduino-mega-2560-toolchains-and-upload
board_id: arduino-mega-2560
section_id: toolchains-and-upload
source_refs: [source-arduino-mega-2560-official]
---
# 工具准备、编译和写入

ChatMaker 的入口是 `chatmaker-hardware --board-id arduino-mega-2560`。这个入口使用板卡记录指定的 Arduino AVR 核心和 ATmega2560 编译目标。准备、编译和写入都可通过这一入口完成。[Arduino AVR Boards 1.8.8 的 Mega 定义](https://github.com/arduino/ArduinoCore-avr/blob/1.8.8/boards.txt)

1. **先检查电脑**。加上 `--action doctor`。出现 `ready_for_compile: true`，可以直接编译。只想了解工具时，做到这一步即可。
2. **有缺件时先看计划**。加上 `--action prepare-environment --dry-run`，查看缺少的部分。显示 `remaining_download_bytes: 0` 时，所需组件已安装或已有校验通过的压缩包。首次解包仍可能花一些时间。要实际准备时，去掉 `--dry-run`。Apple 芯片 Mac 若报告 `requires_rosetta`，按系统提示准备 Rosetta，再跑检查。
3. **只编译**。加上 `--action compile --sketch` 并填入作品的 `.ino` 文件或草稿目录。主 `.ino` 文件名要和它所在的目录同名。含空格的路径用引号括起。返回编译成功并生成 `.hex` 后，可以继续连板。
4. **确认板子和端口，再写入**。插板后用 `--action ports` 查看列表，利用拔插前后新增的端口定位这块板。关掉占用该端口的串口监视器。确认实物型号后，用 `--action compile-upload --board-confirmed --port` 和实际端口，再传入同一个 `--sketch`。已确认板型和端口时也可让 ChatMaker 用 `run` 将缺件准备、编译和写入串起来。
5. **写完马上观察**。Blink 例程看 `L` 灯是否持续按写入的节奏亮灭。串口作品核对电脑端读到的数据。需要上电自启时，再断电重接验证一次。

下一个作品沿用同一个 ChatMaker 工具目录，可复用已校验的安装和缓存。课堂若已经在用 Arduino IDE 2，手动选 `Arduino AVR Boards → Arduino Mega or Mega 2560`，处理器选 `ATmega2560 (Mega 2560)`，然后选实际端口。工具栏的勾是编译检查，右箭头是写入。[Arduino IDE 写入指南](https://docs.arduino.cc/software/ide-v2/tutorials/getting-started/ide-v2-uploading-a-sketch/)
