# 星核板七模块 Mind+ 1.8 编译验证

验证日期：2026-08-18

## 结论

七个 ChatMaker 自有模块示例都通过了真实编译。每次编译的退出码均为 `0`，并生成了 application 与 partitions 二进制文件。

这次只验证“代码可以编译”。没有执行烧录、串口读取、重启观察、模块效果或机械适配，因此这些状态仍为 `unverified`。

## 固定环境

- 工具链：Mind+ 1.8 自带 `arduino-builder`，Arduino IDE 兼容版本 `10819`
- 编译完成时间：2026-08-18 02:03:47 至 02:14:54（Asia/Shanghai）；各 Recipe 保存精确 `completed_at`
- 当前目标：`dfrobot:mpython:mpython:FlashMode=dio,FlashFreq=80,UploadSpeed=1500000,DebugLevel=none`
- 命令模板：`arduino-builder -compile -fqbn=<当前目标> -build-path $TEMP/starcore-mindplus-builds/<build-id> examples/chatduino/starcore/<recipe-id>/<recipe-id>.ino`
- 工具链和临时目录均使用占位符记录，报告不保存本机绝对路径。

## 七项结果

| Recipe | Exit | Flash | RAM | Source SHA-256 | Application SHA-256 | Partitions SHA-256 |
| --- | ---: | ---: | ---: | --- | --- | --- |
| `starcore-idmd-0001-rgb-pwm` | 0 | 237360 B (18%) | 17820 B (6%) | `cd654d952af092e3784fe8cf5bfdd7c7f4f0e353cd2c8b3a167b95a4e73a020c` | `bd0e0d088fcbce21271fce57d7bef94a3b5d726f5c418632fc81130f056e7a66` | `efba4421982bd177695a2e2091828fe3b6aa42076be3844a84f0fb08085cead4` |
| `starcore-idmd-0002-serial-mp3` | 0 | 238692 B (18%) | 17844 B (6%) | `50e6596a60140733148ef009cdadcfca64af4e24621d1f74d95e40ba8109b33a` | `899f668ccf2a491ac0ff37a73c769eba07d3536aed53fba18ebcdaadffee69a1` | `efba4421982bd177695a2e2091828fe3b6aa42076be3844a84f0fb08085cead4` |
| `starcore-idmd-0021-oled-message` | 0 | 270032 B (20%) | 17812 B (6%) | `938a92ea08d9f8baf37ff85c8cfdf44fff1724f977ff71ef29ae92dce2d4e8d1` | `557409ecba570f05e696a46e229f13dc2cc49c3d264d893ed57db970894176bd` | `efba4421982bd177695a2e2091828fe3b6aa42076be3844a84f0fb08085cead4` |
| `starcore-idms-0001-button-input` | 0 | 237016 B (18%) | 17820 B (6%) | `9f77a2f2738dc93029218d8b892e4ceaaae1d5e9a6772c5dca57f4ab161769b7` | `fec5a506638a43b7f1875f6ec13e503082075f37e47582117ad1322be256bd36` | `efba4421982bd177695a2e2091828fe3b6aa42076be3844a84f0fb08085cead4` |
| `starcore-idms-0003-potentiometer-read` | 0 | 238776 B (18%) | 17956 B (6%) | `14aa6153d41758be8732e9d0779009fbef3c21080381def448493ea25dc6fe68` | `7eb4d9614de0136d9a143296bbc69aec442e0c818c9aee1f0aed8688792d96aa` | `efba4421982bd177695a2e2091828fe3b6aa42076be3844a84f0fb08085cead4` |
| `starcore-idms-0008-dht11-serial` | 0 | 238356 B (18%) | 17860 B (6%) | `a212f96006f7c129954493c12777d4d2dedc3a3c40ba72a45692a9e666dc0cca` | `2db693ffa410ebd44f3e8f33e1c54ceddd01fa21cd354a9c7c19f607784ab9a7` | `efba4421982bd177695a2e2091828fe3b6aa42076be3844a84f0fb08085cead4` |
| `starcore-idms-0009-ultrasonic-distance` | 0 | 237972 B (18%) | 17828 B (6%) | `449904d4241edf18eb62e1af84e7b66535d1bd9dec03142fe7f3bdf3518e8eb2` | `60a5c6e0727f012c9d366852639412be5fe4a52ff3021201bf054c355c08748b` | `efba4421982bd177695a2e2091828fe3b6aa42076be3844a84f0fb08085cead4` |

每个 Recipe 内还保存了自己的证据 ID、清洗后的命令、`$TEMP` artifact 路径和上述哈希。Component 只引用对应证据 ID，不复制编译明细。

## 过程备注

OLED 示例在一次并行工具链尝试中只返回了无源码诊断的 `exit status 1`。停止并行后，使用同一源码与同一目标顺序重跑，退出码为 `0` 并生成完整产物；最终证据取顺序重跑结果。其余示例第一次顺序执行即通过。

工具链还输出了其自带 `Wire` 库的重载候选提示和一个库分类警告；它们没有使编译失败，但不属于硬件效果证据。
