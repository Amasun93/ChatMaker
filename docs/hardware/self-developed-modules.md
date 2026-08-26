# ChatMaker 自研硬件模块使用边界

ChatMaker 收录交接包中的完整 23 项自研硬件：1 块主控板、4 个显示/声音/灯光模块、3 个供电与连接模块、2 个执行器驱动模块、12 个传感/开关模块，以及 1 个模拟三轴加速度模块。

普通目录标题只显示学生和老师能直接理解的中文名称。`IDMC`、`IDMD`、`IDMF`、`IDMM`、`IDMS` 编号保留在底层身份、来源追踪和生成链中。

## 三种可用状态

- `guidance_ready`：已有足够的受控来源和 ChatMaker 路径，可生成接线/编程指导；编译、烧录、串口和实物效果仍分别验证。
- `teacher_validation`：可生成资料核对和最小实验任务；未知电压、引脚、有效电平、版本或协议必须由老师/实物确认。
- `retrieval_only`：当前只做资料检索、风险说明和测量清单，不生成 GPIO 接线、协议命令或控制代码。

## 调用方式

```powershell
chatmaker-catalog --request-json '{"action":"list_modules"}'
chatmaker-catalog --request-json '{"action":"module_guide","module":"U 形槽光电计数器"}'
chatmaker-catalog --request-json '{"action":"project_task","module":"四路直流电机驱动模块","goal":"做一辆小车"}'
```

机械数据中的二维外形可用于检索和初步布局。正式外壳、孔位、避让和装配仍要回到所列 STEP/DXF，并保留实物公差和 `physical_fit: unverified` 边界。
