from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DesignDirection:
    id: str
    name: str
    feeling: str
    primary_interaction: str
    best_for: str
    tradeoff: str
    palette: tuple[str, ...]
    typography: str
    motion: str
    aesthetic: str
    advanced: bool = False


_DIRECTIONS: dict[str, tuple[DesignDirection, ...]] = {
    "classroom-tool": (
        DesignDirection(
            id="editorial-signal",
            name="编辑部信号板",
            feeling="清醒、有观点，像一张会回应的课堂海报",
            primary_interaction="学生轻触主按钮，数字与状态立即回应",
            best_for="投票、反馈、提问收集和大屏展示",
            tradeoff="强调一件核心事情，不适合同时堆很多统计卡片",
            palette=("#f3ead8", "#18201c", "#e5482e", "#f5b942"),
            typography="serif-display",
            motion="staggered-reveal",
            aesthetic="editorial-signal",
        ),
        DesignDirection(
            id="tactile-spark",
            name="触感实验台",
            feeling="活泼、像可以按动的教具，但不幼稚",
            primary_interaction="大尺寸控件带来按压、回弹和即时计数反馈",
            best_for="低龄课堂、热身活动和快速分组",
            tradeoff="动感更强，长时间投屏时需要减少连续动画",
            palette=("#fff7d6", "#24213a", "#ff6b5d", "#54c6a9"),
            typography="rounded-display",
            motion="spring-press",
            aesthetic="tactile-spark",
        ),
        DesignDirection(
            id="quiet-focus",
            name="安静聚焦页",
            feeling="克制、平静，让全班注意力集中在一个问题上",
            primary_interaction="单一选择区配合柔和的进度变化",
            best_for="计时、反思、阅读和安静反馈",
            tradeoff="视觉刺激较少，不适合作为热闹的活动开场",
            palette=("#e8eee9", "#17221d", "#547567", "#d2a85a"),
            typography="humanist-display",
            motion="slow-fade",
            aesthetic="quiet-focus",
        ),
        DesignDirection(
            id="field-notebook",
            name="野外观察册",
            feeling="好奇、自然，像一本被全班共同写满的科学观察册",
            primary_interaction="学生把观察贴到不同线索区，页面保留纸张叠放的反馈",
            best_for="探究记录、校园观察和项目式学习线索墙",
            tradeoff="手作层次很有记忆点，但不适合同时展示密集精确数据",
            palette=("#e8dfc4", "#253126", "#b4492f", "#79915a"),
            typography="field-notes",
            motion="paper-settle",
            aesthetic="field-notebook",
            advanced=True,
        ),
        DesignDirection(
            id="stage-cue",
            name="舞台提示器",
            feeling="聚光、果断，像活动现场等待全班一起触发的舞台机关",
            primary_interaction="主操作像打下一个舞台 cue，灯带与文字按节拍切换",
            best_for="开场倒数、集体挑战和成果发布现场",
            tradeoff="戏剧张力很强，安静阅读或长时间填写时会显得过重",
            palette=("#15130f", "#f5ead0", "#d34832", "#d6a94f"),
            typography="theatre-poster",
            motion="cue-sweep",
            aesthetic="stage-cue",
            advanced=True,
        ),
    ),
    "hardware-interface": (
        DesignDirection(
            id="device-console",
            name="设备状态台",
            feeling="可靠、清楚，像一台经过设计的科学仪器",
            primary_interaction="先看清连接状态，再发送控制命令并等待设备回执",
            best_for="传感器看板、灯光控制和课堂硬件演示",
            tradeoff="状态信息优先，装饰性会主动让位给可读性",
            palette=("#e7ece8", "#101714", "#2e7d62", "#f0a43c"),
            typography="technical-editorial",
            motion="state-transition",
            aesthetic="device-console",
        ),
        DesignDirection(
            id="tactile-control",
            name="触控遥控器",
            feeling="直接、有力，像手里握着一块专用控制面板",
            primary_interaction="用大按钮和滑杆发送动作，页面持续显示模拟或真实状态",
            best_for="手机控制灯光、舵机和互动装置",
            tradeoff="主动作突出，因此复杂数据分析需要另开详情区",
            palette=("#f4efe5", "#1f2430", "#d84b36", "#69a88d"),
            typography="condensed-display",
            motion="physical-press",
            aesthetic="tactile-control",
        ),
        DesignDirection(
            id="field-monitor",
            name="现场观察窗",
            feeling="冷静、连续，适合盯住变化而不是频繁操作",
            primary_interaction="连接后观察时间线、最新读数和异常提示",
            best_for="环境数据、长期传感器观察和实验记录",
            tradeoff="控制动作较弱，更适合读数据而不是玩互动",
            palette=("#e9e7df", "#182126", "#4d7483", "#c96947"),
            typography="monospace-accent",
            motion="data-pulse",
            aesthetic="field-monitor",
        ),
        DesignDirection(
            id="flight-deck",
            name="任务飞行甲板",
            feeling="紧张、精确，像只保留关键仪表的任务控制席",
            primary_interaction="先解锁主控，再用醒目的状态轨道确认每一道命令",
            best_for="机器人任务、竞赛装置和需要明确安全顺序的控制页",
            tradeoff="操作秩序非常清楚，但对只看一个温度的简单项目会显得隆重",
            palette=("#111817", "#e9f0dc", "#f08b32", "#6f9186"),
            typography="mission-condensed",
            motion="scan-lock",
            aesthetic="flight-deck",
            advanced=True,
        ),
        DesignDirection(
            id="botanical-lab",
            name="植物实验站",
            feeling="温和、有生命感，让传感器读数像正在生长的样本",
            primary_interaction="触摸样本环切换观察维度，控制结果以生长纹理回应",
            best_for="植物监测、生态装置和低压持续观察",
            tradeoff="自然隐喻很亲近，但快速告警仍需额外使用硬边界和高对比色",
            palette=("#eef0d8", "#243229", "#5f7f50", "#d5864c"),
            typography="botanical-serif",
            motion="growth-ring",
            aesthetic="botanical-lab",
            advanced=True,
        ),
    ),
    "mini-game": (
        DesignDirection(
            id="reaction-rush",
            name="闪光反应赛",
            feeling="轻快、直接，每次命中都有立刻得到奖励的感觉",
            primary_interaction="在倒计时内不断点击或轻触随机出现的目标",
            best_for="反应训练、课堂热身、找目标和限时收集",
            tradeoff="上手最快，但玩法深度主要来自节奏、连击和目标变化",
            palette=("#fff8dd", "#17233d", "#ff5d73", "#ffd166"),
            typography="playful-display",
            motion="pop-and-relocate",
            aesthetic="reaction-rush",
        ),
        DesignDirection(
            id="dodge-collect",
            name="躲避收集场",
            feeling="紧张但不挫败，移动一下就能马上理解玩法",
            primary_interaction="左右移动角色，收集奖励并避开障碍物",
            best_for="太空、环保、运动、交通和角色冒险主题",
            tradeoff="游戏感更强，但需要同时照顾键盘和手机触控",
            palette=("#eaf8ff", "#10233c", "#2ec4b6", "#ff9f1c"),
            typography="arcade-rounded",
            motion="fall-and-dodge",
            aesthetic="dodge-collect",
        ),
        DesignDirection(
            id="drag-puzzle",
            name="拖拽解谜桌",
            feeling="像整理一张会回应的桌面，安静、清楚又有完成感",
            primary_interaction="把不同物件拖到正确位置，逐步完成挑战",
            best_for="分类、排序、拼装、知识配对和空间规划",
            tradeoff="很适合课堂内容，但需要认真设计答案与错误反馈",
            palette=("#f5f0ff", "#25203a", "#7c5cff", "#f6c453"),
            typography="friendly-editorial",
            motion="drag-snap",
            aesthetic="drag-puzzle",
        ),
        DesignDirection(
            id="platform-hop",
            name="轻量平台跳跃",
            feeling="有探索感，角色移动、跳跃和落点形成连续节奏",
            primary_interaction="控制角色移动和跳跃，抵达终点并收集沿途物件",
            best_for="冒险叙事、关卡挑战和连续运动玩法",
            tradeoff="需要更精细的碰撞、镜头与关卡设计，修改成本高于基础玩法",
            palette=("#edf7e8", "#183126", "#e7653c", "#f2c14e"),
            typography="adventure-display",
            motion="run-jump-land",
            aesthetic="platform-hop",
            advanced=True,
        ),
        DesignDirection(
            id="rhythm-lights",
            name="节奏灯阵",
            feeling="像一场小型演出，声音、光点和操作保持同一节拍",
            primary_interaction="跟随节奏依次触发亮起的按键并积累连击",
            best_for="音乐、舞台、节奏训练和多人轮流挑战",
            tradeoff="表现力很强，但音频同步和无声替代方案需要额外设计",
            palette=("#15152b", "#f8f5ff", "#ff4fa3", "#4deeea"),
            typography="stage-digital",
            motion="beat-pulse",
            aesthetic="rhythm-lights",
            advanced=True,
        ),
    ),
}


def validate_advanced_flag(advanced: object) -> bool:
    if type(advanced) is not bool:
        raise TypeError("advanced must be a boolean")
    return advanced


def suggest_directions(
    kind: str,
    desired_feeling: str | None = None,
    limit: int | None = None,
    *,
    advanced: bool = False,
) -> list[DesignDirection]:
    advanced = validate_advanced_flag(advanced)
    try:
        directions = list(_DIRECTIONS[kind])
    except KeyError as exc:
        raise ValueError(f"unsupported ChatWeb project kind: {kind}") from exc

    if not advanced:
        directions = [direction for direction in directions if not direction.advanced]

    if desired_feeling:
        needle = desired_feeling.casefold()
        directions.sort(
            key=lambda item: needle not in f"{item.name} {item.feeling} {item.best_for}".casefold()
        )

    if limit is None:
        limit = len(directions) if advanced else 3
    return directions[: max(1, min(len(directions), limit))]
