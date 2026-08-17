# 设备与工艺卡升级方法

ChatMaker Knowledge 将“放什么”和“怎么制造”分开管理：

- `knowledge/mechanical/boards/` 保存板卡与模块的外形、孔位和禁入区。
- `knowledge/fabrication/equipment/` 保存设备或加工软件的能力、图层和顺序规则。
- `knowledge/fabrication/materials/` 保存材料厚度、用途和校准状态。
- `knowledge/fabrication/source-registry.json` 登记来源，不把未经确认的功率、速度写成通用事实。

## 新增一张设备卡

1. 找到设备厂商或软件的官方手册，登记到 `source-registry.json`。
2. 复制现有设备卡，只保留能够追溯的格式、工作区、图层、加工顺序和安全规则。
3. 具体功率、速度和次数必须与“设备型号 + 材料 + 厚度”绑定；没有真实测试时保持 `calibration-required`。
4. 用 `fabrication-equipment.schema.json` 检查格式。
5. 在 `knowledge/fabrication/index.json` 增加入口，再让 ChatCAD 通过 `cad_fabrication_get` 读取。

## 新增一张材料卡

1. 建立稳定 `material_id`，记录材料类型与默认厚度。
2. 对割缝、功率、速度和次数分别标明验证状态，未知值使用 `null`，不要猜测。
3. 用 `fabrication-material.schema.json` 检查格式，并更新索引。

当前 Alpha 默认组合是：

```text
设备：lasermaker-generic
材料：wood-sheet-3mm
厚度：3.0 mm，可调整
功率与速度：calibration-required
```

首次加工仍需先做材料测试矩阵或小尺寸试片；“生成文件”不等于“实体加工已验证”。
