# ChatCAD Alpha 设计

ChatCAD 是 ChatMaker 的机械创作伙伴。第一版只做一条完整路径：AI 读取板卡机械资料，生成参数化安装底板，用户在浏览器预览实验室中调整参数，并下载 DXF、SVG、OpenSCAD 和 STL。

## 首批板卡

- Arduino Nano Classic：Arduino 官方 CAD。
- Arduino Uno R3：Arduino 官方 CAD。
- DOIT ESP32 DevKit V1：社区机械参考，板型差异较大，紧配前必须实测。
- IDMC-0001 星核板 v4.2.2：由内部 DXF/STEP 清洗出的公开尺寸；原始制造文件不进入仓库。

机械资料存放在 `knowledge/mechanical/boards`，与 ChatDuino、ChatWeb 共用同一稳定 `board_id`。每个资料明确记录来源等级和实体装配状态。

## 最小工作流

1. AI 确认板卡和作品效果。
2. ChatCAD 提供两到三个简单方案。
3. `chatmaker-cad` 读取机械资料并生成安装底板项目。
4. `preview-lab.html` 左侧调整间隙、厚度、安装柱和孔径，右侧即时显示俯视图。
5. 页面按当前参数下载 DXF、SVG、SCAD 或 STL。

Alpha 只支持规则安装底板和安装柱，不支持自由曲面、复杂网格布尔或实体装配保证。测试只覆盖四块板可读取、一个项目可生成、参数页面存在和四种文件可导出。
