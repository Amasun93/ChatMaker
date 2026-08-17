# ChatMaker 星核板七模块独立迁移设计

## 目标

将七个星核板自研模块的公开使用能力完整迁入 ChatMaker，使用户只从 ChatMaker 进入，由 ChatMaker 调度 ChatDuino、ChatWeb 和 ChatCAD 三个内部 Skill。正式运行、安装、知识读取、编译和 CAD 生成不得依赖旧 Nano、旧星核板或旧行空板 Skill 的路径、安装状态或文件内容。

首批模块为：

- `IDMD-0001` RGB 灯
- `IDMD-0002` 串口 MP3
- `IDMD-0021` OLED 1.3 寸
- `IDMS-0001` 按钮
- `IDMS-0003` 电位器
- `IDMS-0008` DHT11 温湿度
- `IDMS-0009` 超声波

## 保留现有架构

不新增无必要的 `modules/` 目录，不改变四个 Skill 的源码分层：

```text
ChatMaker（唯一用户入口）
├─ ChatDuino（内部硬件 Skill）
├─ ChatWeb（内部网页 Skill）
└─ ChatCAD（内部 CAD Skill）
        ↘ ChatMaker Knowledge（共享事实）
```

源码仍分别维护在 `skills/chatmaker`、`skills/chatduino`、`skills/chatweb` 和 `skills/chatcad`。目录同级只代表独立维护和测试，不代表产品职责平行。README、安装提示和默认使用说明只引导用户从 ChatMaker 开始；内部三个 Skill 保留独立说明、参考资料和测试，并由 ChatMaker 自动路由。只有 ChatMaker 提供面向用户的 `agents/openai.yaml` 入口元数据；内部 Skill 继续随包安装，但不再各自显示一个默认用户提示。若某个宿主技术上强制要求元数据，替代方案只能把它标成 ChatMaker 内部模块并将默认提示转回 ChatMaker，不能恢复为并列用户入口。

## 旧 Skill 迁移边界

旧 Skill 只在开发阶段作为一次性迁移输入。迁移过程必须经过资料盘点、来源核对、公开边界清洗、重新建卡、重新编写示例和重新验证。不得在 ChatMaker 中：

- 引用旧 Skill 的本地绝对路径；
- 在运行时打开或搜索旧 Skill；
- 根据旧 Skill 是否安装决定功能是否可用；
- 把旧 Skill 的制造源文件或原始档案复制进公开仓库；
- 在资料不足时回退到旧 Skill 或通用模块猜测。

缺少可信资料的字段保持 `unverified` 或明确不支持。测试必须在临时环境中模拟旧 Skill 完全不存在，并证明 ChatMaker 的目录、发行包和运行时仍能完成知识查询、示例发现、编译准备和 CAD 资料读取。

WorkBuddy 的正式 MCP 注册键使用 ChatMaker 自有名称。历史键只有在其命令精确指向当前 `chatmaker.integrations.mcp` 时才安全迁移；真正属于旧独立插件的同名配置必须原样保留。

## 数据模型

七个自研模块各自拥有稳定组件 ID，不能与功能相似的通用组件合并。例如 `IDMS-0008` 与 `dht11-three-pin-module` 可以共享传感器类别，但板型、供电、默认引脚、Mind+ API、机械尺寸和证据状态必须分别保存。

每张组件卡包含：身份辨认、供电与逻辑电平、接口和引脚、星核板兼容规则、Mind+ 扩展和头文件、示例路径、常见故障、板卡说明以及四级验证状态。配方卡引用精确的自研组件 ID 和 `idmc-0001-starcore-v4-2-2`，不通过中文名称模糊匹配。

编译证据由精确的 recipe/example 拥有，记录 source hash、目标、退出码和构建结果。组件卡的 `code_compiled` 只能引用该证据 ID，不能复制成第二份含义不同的证明。旧报告只作为 `historical_lead`，不进入当前验证门。

首批迁移必须特别防止三组错误合并：`IDMD-0001` 是共阳三路 PWM RGB 灯，不是 WS2812；`IDMS-0001` 是普通三线数字按钮，不是 I2C RGB 按钮；`IDMS-0009` 当前课堂路线是 `DFRobot_URM10` GPIO 超声波，不是 `sen0304` I2C 超声波。这些相似模块可被搜索到，但不能共享接线、库、API 或编译证据。

ChatMaker Knowledge 的星核板章节负责解释模块选择、接线、库、示例和排错；规范数字仍以 canonical board/component/recipe 记录为准，避免正文复制后发生冲突。

MP3 的 P15/P16 UART 和 5V 供电必须先进入星核板 canonical 记录并通过来源验证，配方才能引用。不能为了通过 schema 临时虚构 P16 或电源引脚。现有通用 OLED、DHT11、按钮、电位器、RGB 和超声波卡可以继续存在，但一份星核板编译证据只能归属于真实使用的硬件身份，不能同时证明通用件和自研件。

## 编程与接线流程

ChatMaker 确认精确板卡身份后调用 ChatDuino。ChatDuino 读取板卡和组件记录，先完成供电、逻辑电平、I2C/UART、启动脚和引脚冲突检查，再输出一个断电接线 `text` 代码块和一个完整 `cpp` 代码块。

七个模块各有至少一个可独立编译的示例。当前编译目标固定为：

```text
dfrobot:mpython:mpython:FlashMode=dio,FlashFreq=80,UploadSpeed=1500000,DebugLevel=none
```

Mind+ 2.0 目标只保留为历史知识，不能替代当前编译目标。编译成功只更新 `code_compiled`；没有实体板时，烧录、重启、串口输出、传感器读数、声音、显示和物理效果继续保持 `unverified`。

旧资料中的布尔“编译通过”或验证报告只能记录为历史线索，不能直接提升为 ChatMaker 当前编译证据。七个发布示例必须重新保存源文件哈希、当前目标、退出码和构建结果。OLED 使用 `MPython.h` 的全局 `display`，MP3 使用 `DFRobot_SerialMp3.h`，DHT11 使用 `DFRobot_DHT.h` 并按当前库行为交替读取温湿度，超声波使用 `DFRobot_URM10.h` 的 GPIO 路线。

## 机械资料与 ChatCAD

ChatCAD 使用与 ChatDuino 相同的组件 ID。当前运行层只有板卡机械档案，因此本轮先建立独立的组件机械档案 schema、目录和读取接口，再接入模块数据。MP3、OLED、DHT11 和超声波可迁移已经清洗并具备来源记录的面板开孔与固定孔资料。RGB、按钮和电位器只发布已有可信板框、孔距或固定孔；旋钮直径、器件突出高度、接口中心等未确认数据不得用演示值补齐。

机械记录必须标明 `source_reviewed` 和 `physical_fit`，记录级保存来源 ID，每个几何特征再保存其证据状态。ChatCAD 提供稳定的 `component-profile` 读取动作供 CLI 和 MCP 共用。生成 DXF、SVG、OpenSCAD 或 STL 只证明文件生成成功，不能提升为实体装配通过。制造源文件继续保留在私有资料区，公开仓库只保存清洗后的必要尺寸与来源 ID。

## 错误处理

- 身份不清：询问模块编号或丝印，不按相似外形猜测。
- 供电或信号电平不清：停止接线和上传建议，标记待确认。
- Mind+ 扩展缺失：报告缺少的扩展或头文件，不切换到陌生库。
- 编译失败：保留结构化错误，修正完整程序后重试，不能把失败写成已验证。
- 机械字段不足：只生成已验证部分，明确列出待实测项。
- 旧 Skill 缺失：视为正常环境，不触发降级或报错。

## 验收

1. 七个自研模块在目录中保持独立稳定 ID，并能通过中文名称和编号检索。
2. 每个模块至少有一个完整星核板示例和对应配方。
3. 所有计划发布的示例使用当前 Mind+ 1.8 目标真实编译并记录证据。
4. 接线输出遵守断电、逐线、简单直白的教师/学生格式。
5. 可信机械记录能被 ChatCAD 读取；不可信字段保持未验证。
6. 临时清洁环境中不存在任何旧 Skill 时，ChatMaker 功能和发行测试仍通过。
7. 公共文件扫描不包含私有制造源、绝对源路径或旧 Skill 运行引用。
8. 全量自动测试、独立审查、全局安装刷新和 GitHub `main` 推送均成功。

## 本轮不做

- 不迁移全部 23 种自研模块；
- 不接入行空板 M10/K10；
- 不实现不依赖 Mind+ 的新工具链；
- 不声称完成任何未获得实体证据的烧录或物理效果；
- 不为了单入口重排四个 Skill 的源码目录。
