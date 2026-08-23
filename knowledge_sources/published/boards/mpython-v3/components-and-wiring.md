---
schema_version: "1.0"
kind: knowledge-page
stable_id: mpython-v3-components-and-wiring
board_id: mpython-v3
section_id: components-and-wiring
source_refs: [source-mpython-v3-official]
---
# 先使用 3.0 的板载能力

3.0 已带彩屏、六轴、磁场、数字光线、双麦克风、音频编解码、功放、1W 扬声器、三颗 RGB、A/B 键和六个触摸键。AI 应先确认项目能否直接使用板载器件，再决定是否连接外部模块。

外接模块需要同时核对 3.3V 逻辑、供电电流、接口和共享总线。不要把板载扬声器当成可以直接驱动任意外部大功率喇叭的输出。

