# ChatMaker 板卡 LLMWiki 与渐进式知识包设计

## 目标

ChatMaker 建立一个所有创作模块共用的板卡知识底座。用户和 AI 以板卡为入口，逐层读取硬件、软件、库、案例、网络和未来机械资料；元器件仍保持单一来源，不复制到每块板卡目录。首次安装只带运行核心、现有规范数据、紧凑索引和必要安全说明；详细 LLMWiki 章节按板卡从 GitHub 官方知识包自动下载。

本阶段覆盖 Arduino Nano Classic、Arduino Uno R3、DOIT ESP32 DevKit V1 和现有 12 类元器件。ChatCAD 只保留未来接口说明，不创建 Skill、CLI、MCP 工具或 DXF/3D 生成功能。

## 核心决定

### 板卡是入口，规范事实保持单一来源

`packs/boards/*.yaml`、`packs/components/*.yaml` 和 `packs/recipes/*.yaml` 继续保存可计算的精确事实和证据状态。LLMWiki 不复制针脚、电压、编译状态或尺寸数字，而是引用稳定 ID，提供适合人和 LLM 阅读的知识页、流程页和样本页。

```text
板卡入口
├─ 规范板卡记录
├─ 兼容元器件摘要
├─ 相关案例摘要
└─ LLMWiki 紧凑索引
   ├─ 章节 ID、用途和适用模块
   └─ 官方知识包 ID
```

通用元器件只保存一份。板卡入口通过反向索引展示兼容关系；打开 Nano、Uno 或 ESP32 下的 LED，仍然读取同一个 `basic-led` 记录和同一份证据状态。可静默安装的板卡知识包只允许包含 LLMWiki 章节，不允许携带或覆盖 canonical board/component/recipe YAML。

### LLMWiki 是公共知识层，不属于 ChatCAD

ChatMaker 用入口页理解板卡并路由；ChatDuino 在接线、代码和编译前读取安全、针脚和工具链章节；ChatWeb 只在硬件交互项目中读取网页与通信章节。独立网页项目不加载板卡知识。

未来 ChatCAD 使用同一稳定 board ID 读取机械资料，但本阶段不能成为运行路由，也不能以文档存在为由报告 CAD 能力已经实现。

### 原始资料、发布源码和核心安装严格分开

```text
knowledge_sources/raw       原始资料，本地编辑区，永不发布
knowledge_sources/cleaned   清洗结果，本地审阅区，永不发布
knowledge_sources/manifests 来源、许可、hash、清洗和复核状态
knowledge_sources/published 获准发布的板卡 LLMWiki 章节源码
packs/llmwiki/boards        核心内置紧凑索引，不含详细正文
distribution/packs          构建后的每板 .cmpack
distribution/registry       签名注册表与 detached signature
```

入库顺序固定为：收集原始资料、清洗、结构化、来源核对、复核、发布批准。`cleaning_verified`、`source_reviewed` 和 `publication_approved` 是不同状态，不能互相替代。迁移旧资料不会自动把未验证状态升级为已验证。

### 第一安装物与渐进下载

主要安装物定义为 `ChatMaker-Core-<version>.zip`。它包含 Python 运行层、三个现有 Skill、schema、3/12/14 规范记录、紧凑板卡索引、现有可运行案例、安装说明和必要许可证；不包含详细 LLMWiki 正文、知识原始资料、测试、开发缓存或已构建的可选知识包。

详细正文按板卡分为三个只读知识包：

```text
chatmaker-board-arduino-nano-classic-wiki
chatmaker-board-arduino-uno-r3-wiki
chatmaker-board-esp32-devkit-v1-wiki
```

读取章节时默认 `auto_install=true`。本地缺少正文时，LLMWiki reader 自动调用幂等 `ensure(pack_id)`；第一次下载、校验并激活，第二次直接复用，离线时使用已经缓存或安装的精确版本。

### 统一读取合同

CLI 和 WorkBuddy MCP 共用两个动作：

```json
{"action":"index","board_id":"arduino-nano-classic","consumer":"chatduino"}
{"action":"section","board_id":"arduino-nano-classic","consumer":"chatduino","section_id":"identify-and-safety","auto_install":true}
```

v1 不实现分页 cursor。每个章节必须小于发布上限并一次完整返回，避免把安全警告或代码块从中间切断。未知板卡、章节、consumer、离线缺包和信任失败分别返回稳定错误码，不回退到相似板卡。

### 官方分发与信任

官方注册表固定为：

```text
https://raw.githubusercontent.com/Amasun93/ChatMaker/main/distribution/registry/registry.json
https://raw.githubusercontent.com/Amasun93/ChatMaker/main/distribution/registry/registry.sig.json
```

`registry.sig.json` 保存 `key_id`、`algorithm=ed25519` 和 base64 signature；签名对象是 `registry.json` 的原始字节。公开信任锚随核心发布，私钥只从仓库外部路径传入签名工具，永不写入 Git、日志或发布包。

注册表包含单调递增 sequence、生成/过期时间和每个包的不可变 URL、长度、SHA-256、核心兼容范围。知识包 URL 指向包含该归档的精确 Git commit，而不是可变 `main`。本地按 registry/key 保存已接受的最高 sequence，拒绝回放旧注册表。密钥轮换由核心中的多信任锚完成；撤销必须通过新的核心版本更新信任锚。

### 内容包事务与 Windows 安全

1. 验证允许列表、注册表签名、key 状态、sequence 和有效期。
2. 下载到内容寻址缓存的 `.part` 文件。
3. 校验长度、SHA-256、核心版本和 schema 兼容范围。
4. 安全解压到 staging，拒绝绝对路径、`..`、符号链接、安装钩子、UNC、盘符相对路径、ADS、保留设备名、尾随点/空格和大小写重复路径。
5. 校验逐文件 hash、清单、知识 schema 和 canonical 引用。
6. 原子移动到 `store/<pack-id>/<version>` 不可变目录。
7. 激活前重新 hash；漂移版本隔离，不继续激活。
8. 原子替换 `active.json`；失败时旧版本继续生效。
9. 回滚只切换到已经完整校验的旧版本。

资源优先级为显式本地覆盖、已激活官方知识包、核心内置索引。只有独立 override 目录能覆盖内容，并必须显示 `provenance=local_override`；官方 store 中的漂移不被当成用户覆盖。

### 静默安装边界

本阶段只支持官方 `knowledge` 包静默安装，不支持 Skill 包和依赖图。驱动、Mind+、Arduino Core、Node、Chromium、系统 PATH、管理员操作、WorkBuddy MCP 配置修改和任何安装钩子继续使用原有显式边界。

### 验证和完成边界

- 知识页存在不等于来源已核对。
- 来源已核对不等于程序已编译。
- 编译成功不等于烧录、串口、网络或实物成功。
- 机械接口说明存在不等于尺寸、DXF、3D 模型或真实装配已验证。
- 当前没有开发板，所有缺少实物证据的门继续保持 `unverified`。
- 合并前验证 feature 和 main 工作树干净、`origin/main` 未意外移动；推送后用 `ls-remote` 确认 GitHub main 等于本地测试提交，再从公共注册表真实自动安装一个知识包。

## 兼容与发布

现有 3/12/14 规范记录数、稳定 ID、catalog search/get 返回结构和三个 Skill 安装语义保持不变。旧 rc1-rc5 文档是历史证据，不倒写。本任务合并并推送 main，但不自动创建公开 Release；核心与知识包构建、干净安装和公共 GitHub 下载均要留下验证记录。
