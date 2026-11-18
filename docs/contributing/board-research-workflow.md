# ChatMaker 新板卡接入流程

发现适合课堂的板卡时，给出**具体型号或官方产品链接**，再说一句想让学生做出的效果。手边有实物时，补上背面的版本标记或照片。ChatMaker 维护者会先查已有支持，再核对是否值得接入、能做哪个课堂示例，以及需要哪些外接模块。

> 推荐示例：这块板是「型号或官方链接」。我想用它带学生做「一个看得见的效果」。如果需要确认版本，我可以拍板子背面。

## 从推荐到接入

1. **确认板子和课程目标。** 查板上名称、版本、芯片和关键外设。遇到相似型号，用板上的字、接口或内存标记确认。记录一个能让老师判断是否适合课堂的作品示例。
2. **查官方资料并建板卡记录。** 从产品页、原理图、引脚图、官方源码和工具文档核对事实。把电压、引脚用途、板载器件、注意事项和适用型号写进结构化记录。涉及外壳时，区分官方尺寸、接口避让尺寸和实物试装。
3. **走通最短开发路线。** 确认用什么工具、首次缺什么、如何复用准备好的环境，以及按什么型号和端口写入。先做一个可复制的小例子，再根据板子的特点选择代表案例。
4. **同一批提交补完八节 Wiki。** 从记录和已查证的来源写给学生和 AI 看。写清不确定的地方，接线和验证门以实际资料为准。未来每次新增板卡，Wiki、索引、来源清单和学生常见问题与板卡记录一起交付。
5. **按证据验收。** 分别记录环境、源码检查、编译、上传或项目同步、串口、断电重启和实物效果。用实际板型试一次目录搜索、Wiki 读取和工具预览。有实板时，再根据项目授权验证写入和效果。

## Wiki 的八个章节

| 章节 | 老师和学生能查到什么 |
| --- | --- |
| `start-here` | 这块板适合做什么，先试哪个例子 |
| `identify-and-safety` | 看哪里确认型号和版本，哪些操作要先断电或确认电压 |
| `pins-and-electrical` | 认哪一排丝印、有哪些共享或启动相关引脚、到哪查完整引脚图 |
| `toolchains-and-upload` | 用哪个现成入口，何时需要准备工具，怎样确认目标和看进度 |
| `components-and-wiring` | 什么已经在板上，哪些模块需要外接，怎么检查已经接好的线 |
| `libraries-and-examples` | 从哪个例子起步，需要哪些库，做完应看到什么 |
| `web-and-protocol` | 板子、串口或网页怎样交换信息，如何分别确认结果 |
| `troubleshooting` | 板子找不到、首次准备慢、编译失败、写入后无效果时，先做什么 |

常见问题用「遇到的现象 → 先做一步 → 看什么结果」来写。保留能让同学照做的型号、丝印和数值，原理讲到能帮助判断为止。只读资料、选板或接线讨论可以直接用 Wiki。需要实际编译或写入时，再按板型查看和准备工具。

## 单一登记入口

- 新板卡只在 `packs/boards/<board-id>.yaml` 手工登记一次；其中 `chatmaker` 指向运行入口和识别方式，`mechanics` 指向机械档案或明确写 `research-required`。
- 新模块只在 `packs/components/<component-id>.yaml` 手工登记一次；机械档案如存在，使用同一个 component ID 放在 `knowledge/mechanical/components/`。
- `python scripts/sync_catalog_registry.py` 从板卡、模块、Knowledge、机械档案和来源清单生成运行时快照。不要再向 Python 文件添加手写板卡白名单。
- Wiki 索引放在 `knowledge/boards/<board-id>.yaml`，来源清单放在 `knowledge_sources/manifests/<board-id>.yaml`，八节正文放在 `knowledge_sources/published/boards/<board-id>/`。章节格式和核验要求见 [Wiki 格式](https://github.com/Amasun93/ChatMaker/blob/main/docs/contributing/knowledge-format.md) 和[来源整理流程](https://github.com/Amasun93/ChatMaker/blob/main/docs/contributing/knowledge-source-pipeline.md)。
- 新板默认用 `chatmaker.knowledge_delivery: source` 从完整源码直接读取 Wiki。安装 Skill 的学生使用随包速查说明。通过官方签名包提供的板卡，从已发布的包读取详情。
- 如果接入的是已有硬件的编译配置，例如已确认芯片和内存的 `nova-esp32`，把配置条件、适用示例和验证范围写到速查说明。确认精确实物型号后，再用独立板卡记录和对应 Wiki 管理。

## 提交前检查

```powershell
python scripts/sync_catalog_registry.py
python scripts/sync_catalog_registry.py --check
python scripts/validate_knowledge_publication.py --root .
python -m unittest tests.test_catalog_registry tests.test_knowledge tests.test_knowledge_pipeline
python runtime/doctor.py --packs
```

自动测试会检查每个板卡记录是否有 Wiki 索引和可读入口。来源检查会核对八节正文、来源清单和声明。代码更新通过验证后，将板卡记录、Wiki 和速查说明一起提交，并写入 [更新日志](../../WHATS_NEW.md)。

## 每块板的完成记录

```text
板卡：精确型号与硬件版本
官方来源：产品页／硬件文档／源码／许可证
工具链：名称、版本、下载来源、是否需要桌面应用
代表案例：案例名与覆盖功能
证据门：环境／编译／上传／串口／断电重启／实体效果
仍未验证：明确列出
Knowledge：板卡记录、索引、章节和知识包状态
```
