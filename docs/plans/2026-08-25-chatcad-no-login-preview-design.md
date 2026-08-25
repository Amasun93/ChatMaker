# ChatCAD 无 MakerWorld 账号时的交付设计

## 目标

学生或小白用户没有 MakerWorld 账号、不能方便登录 MakerLab 时，不把登录当作建模前提，也不让用户等待额外截图或离线渲染。

## 路由

任务卡确认后只问：“你方便登录 MakerLab 吗？”

- 方便登录：`delivery_mode=makerlab-code`，只交付 OpenSCAD 代码和 MakerLab 入口。
- 没有 MakerWorld 账号、不方便登录或明确使用 ChatMaker：`delivery_mode=chatmaker-preview`，同时交付 OpenSCAD 代码和参数仿真页面。

两条路线都属于参数化建模，不再让初学者判断“要不要参数化”。

## 名牌行为

无登录路线使用 ChatMaker 内置 CJK 字体把已确认文字转成 `polygon()`，因此代码不依赖 MakerLab 字体。仿真页面可以调整名牌尺寸、厚度、圆角、孔位、文字缩放、位置和凸起高度，并复制或下载更新后的 OpenSCAD。文字内容已经固化；改字需回 ChatCAD 重新生成。

## 验收

- `chatmaker-preview` 返回 `scad_code` 和 `preview_lab`。
- 名牌页面无需联网即可打开并调整参数。
- 页面不自动创建截图或启动长时间渲染。
- MakerLab 代码路线保持不创建本地输出文件。
