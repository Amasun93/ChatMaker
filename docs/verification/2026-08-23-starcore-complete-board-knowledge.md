# 星核板完整板载能力代表性编译

日期：2026-08-23

目标板：`idmc-0001-starcore-v4-2-2`

当前目标：

```text
dfrobot:mpython:mpython:FlashMode=dio,FlashFreq=80,UploadSpeed=1500000,DebugLevel=none
```

## 验证范围

本轮只验证知识升级新增的两条代表性源码：

1. `MPython.h` 的真实板载 A/B 按键对象和无源蜂鸣器对象可以组合编译；
2. 当前 Mind+ 1.8 ESP32 核心的 `driver/can.h` 可以使用 P13/GPIO18、P14/GPIO19 建立只读 CAN 监听程序。

QMI8658 最小程序已有独立编译证据；七个自研模块继续沿用各自 Recipe 的编译证据。

## 结果

| 程序 | 退出码 | Flash | RAM | 源码 SHA-256 | 应用固件 SHA-256 |
| --- | ---: | ---: | ---: | --- | --- |
| onboard-input-output | 0 | 237368 bytes (18%) | 17812 bytes (6%) | `9efb50ac100a3a2e6dc4dcd3a2e4756cf8c814d24f0c20e20c8b73ac4a780db6` | `27e4ce2e222e5084b3e49d05d33d6b386520445ecccb968132d4bf8319aec898` |
| can-listen-only | 0 | 219744 bytes (16%) | 15284 bytes (5%) | `33d2ee228cd19879f10f468ab0a175772ed8b3a338396e5df28feeebb3d6938b` | `4ce9545874c4ee6376cedf398256fbe6d186ec63877eca680c5136e8f69b5704` |

## 旧核心兼容结论

直接使用 `CAN_GENERAL_CONFIG_DEFAULT(...)` 首次编译失败，因为当前旧版头文件把 `CAN_IO_UNUSED` 的整数值写入 `gpio_num_t` 字段，严格 C++ 编译器报告类型转换错误。改为显式初始化 `can_general_config_t`，并对 `clkout_io`、`bus_off_io` 使用 `(gpio_num_t)CAN_IO_UNUSED` 后编译通过。

因此，当前 Mind+ 1.8 知识示例保留显式初始化写法，不能直接复制面向其他 ESP32 核心版本的默认宏或 `driver/twai.h` 示例。

## 证据边界

本轮没有连接实体星核板，也没有调用上传。按键状态、蜂鸣器声音、USB 自动下载、CAN 收发、波特率、终端电阻、帧协议、重启、串口和物理效果全部保持 `unverified`。
