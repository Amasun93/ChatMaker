# ChatMaker 串口运行层验证

## 已实现接口

```text
serial_list
serial_open
serial_read
serial_expect
serial_write
serial_close
```

WorkBuddy MCP 暴露上述 6 个工具，加上 5 个 Nano 工具、5 个 Uno 工具、4 个 ESP32 精确发现/编译工具和 2 个资料目录工具，当前开发版共 22 个。Codex 使用 `chatmaker-serial` 启动同一运行层的持久 JSONL 会话，并使用 `chatmaker-catalog` 搜索和读取模块资料。

## 自动测试

- 明确的有线端口可以打开一个会话。
- `serial_expect` 返回实际观察到的行和匹配状态。
- `serial_write` 可选择追加换行。
- `serial_close` 释放句柄。
- 蓝牙端口被拒绝，不会建立会话。
- 空读取返回 `no_serial_output`，`serial_evidence` 保持 false。
- UTF-8 替换字符会产生 `malformed_serial_text`。
- 重复启动标记会产生 `restart_loop_suspected`。
- `nano_compile_upload` 在烧录前暂停所有串口会话，流程结束后再尝试恢复。
- 真实 JSONL 子进程可以列出串口并返回结构化结果。

## 当前电脑烟测

Codex 命令与 WorkBuddy MCP 都成功执行 `serial_list`：

```text
port count: 6
bluetooth count: 6
open sessions: 0
```

COM3、COM5、COM6、COM7、COM11、COM12 均为蓝牙虚拟串口。通过 WorkBuddy 调用 `serial_open(COM3, 9600)` 得到：

```text
success: false
error: bluetooth_port_rejected
```

这证明当前机器不会为了完成烟测而错误打开蓝牙端口。

## 证据边界

- 串口接口与会话生命周期：自动测试已验证。
- Codex / WorkBuddy 串口列表和蓝牙拒绝：当前电脑已验证。
- 真实 Nano 运行日志：没有有线 Nano，未验证。
- 预期启动标记、断电重启和传感器数据：没有真实硬件，未验证。
- 串口文本不能单独证明灯、舵机或传感器产生了物理效果。
