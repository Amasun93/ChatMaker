# ChatMaker 自研硬件模块使用边界

ChatMaker 收录交接包中的完整 23 项自研硬件：1 块主控板、4 个显示/声音/灯光模块、3 个供电与连接模块、2 个执行器驱动模块、12 个传感/开关模块，以及 1 个模拟三轴加速度模块。

普通目录标题只显示学生和老师能直接理解的中文名称。`IDMC`、`IDMD`、`IDMF`、`IDMM`、`IDMS` 编号保留在底层身份、来源追踪和生成链中。

## 教学指导与能力门

- 23 项统一为 `guidance_ready`：均可进入项目设计并生成证据约束下的学生指导。
- `capability_gates.programming` 单独区分 `ready`、`conditional` 和 `not_applicable`。供电、并线和 USB 集线器不会为了凑齐流程而生成虚假程序。
- `capability_gates.wiring` 单独区分已确认、项目中分配和版本核对。未知引脚、供电或协议仍保持为空，不因整体状态提升而猜测。
- `mechanical_placement` 与 `panel_cutout` 分开；已确认外形和孔位可以参与布局，未确认的按钮帽、旋钮轴、连接器或开口继续要求实测。
- `historical_use.status=owner_confirmed` 记录项目负责人确认这些模块过去在 Mind+ 项目中使用正常；`current_physical_retest=unverified` 明确本轮没有重新接齐 23 项。

## 调用方式

```powershell
chatmaker-catalog --request-json '{"action":"list_modules"}'
chatmaker-catalog --request-json '{"action":"module_guide","module":"U 形槽光电计数器"}'
chatmaker-catalog --request-json '{"action":"project_task","module":"四路直流电机驱动模块","goal":"做一辆小车"}'
```

22 个配套模块均已进入 ChatCAD 机械 profile，并具有可调用安装孔位。Chat2D 可自动初排或拖动模块，并导出统一 `placements`；Chat3D 使用同一数据生成底板安装柱、顶盖固定孔、已经确认的功能开口和可调侧边线束出口。微动限位开关的 DXF 已确认 20×20 mm 四孔阵列；拨杆活动开口仍需实物尺寸，因此只生成固定孔、不编造活动开口。所有模型继续保留实物公差和 `physical_fit: unverified` 边界。
