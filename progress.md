# Progress · AI 桌面宠物

依据 `handbook.txt` 实现，Python + PySide6。

## 当前文件结构

```
mypet/
├── handbook.txt          # 纲领性文件（只读依据）
├── progress.md           # 本文件
├── .gitignore            # 排除 __pycache__ / _test_log.txt / venv 等
├── requirements.txt      # 依赖：PySide6 / PyYAML / openai
├── start.bat             # 启动脚本（切到脚本目录，跑 main.py，出错暂停）
├── main.py               # 程序入口
├── config.yaml           # 行为与模型连接配置
├── assets/               # GIF 素材（用户提供）
│   ├── idle/stand.gif        # idle
│   ├── walk/walk-left.gif    # 向左走（水平分量向左时播放）
│   ├── walk/walk-right.gif   # 向右走（水平分量向右时播放）
│   ├── walk/get lost.gif     # 走丢（每次走完后按概率播放一次）
│   ├── click/click.gif       # click
│   ├── drag/drag.gif         # drag
│   └── random/              # 「随机动作」的 GIF（决策选中时原地从首帧完整播一遍）
│       ├── pillow talk.gif
│       ├── sleepy.gif
│       ├── dance.gif
│       ├── look around.gif
│       ├── groom myself.gif
│       └── wind flow.gif
└── src/
    ├── __init__.py
    ├── config.py         # 加载 config.yaml，解析相对动画路径为绝对路径
    ├── chat_dialog.py    # 对话框：右键「开始对话」唤起，多轮输入骨架，关闭即清空记忆
    └── pet_window.py     # 主窗口：无边框、透明、置顶；状态机 + 走动/点击/拖动 + 右键菜单 + 对话
```

## 每个文件干什么

| 文件 | 职责 |
|---|---|
| `main.py` | 创建 QApplication，加载配置，显示 PetWindow |
| `start.bat` | 双击启动：切到脚本目录、UTF-8 代码页、运行 main.py，失败时暂停窗口便于看报错 |
| `config.py` | 读取 `config.yaml`，把 animation 里的相对路径（含列表型 `random_actions`）拼成绝对路径 |
| `src/pet_window.py` | 桌宠窗口：Frameless + WA_TranslucentBackground + WindowStaysOnTopHint + Tool；状态机 idle/walk/random/click/drag/lost；QMovie 播 GIF；自主行为循环：待机随机时长（`idle_duration_min/max`，待机固定播 stand.gif）→ 按 `walk_chance`/`random_chance`/`continue_idle_chance` 三项概率加权决策「走动 / 随机动画 / 继续待机」→ 执行动作 → 回待机重新计时；走动 360° 随机、碰边按轴反向、按水平分量切左右走 GIF；随机动作从 `random_actions` 挑一个原地从首帧完整播一遍（不位移，末帧检测，`random_max_ms` 可截断）；左键单击完整播 click、按住移动播 drag（跟手拖动），用户操作打断当前动作；走完按概率播 get lost.gif；右键弹原生 QMenu 菜单（`contextMenuEvent` 先 `_enter_idle()` 回待机并停计时 → `_build_context_menu()` 返回 菜单+动作→回调 映射 → `_exec_menu()` 弹出并按映射分发 → 关闭后恢复计时）；对话管理：`_on_chat_requested` 开对话框（期间 `chat_open` 为真，`_schedule_next_behavior`/`_decide_action` 被拦住保持原地待机），`_on_chat_closed` 恢复计时 |
| `src/chat_dialog.py` | 对话框 `ChatDialog`：QPlainTextEdit 只读日志 + QLineEdit 输入 + 发送按钮；`_history` 仅存本次会话；Esc 快捷键、失活（点外部）即 `close()`，`closeEvent` 清空历史并 emit `closed` 信号（`WA_DeleteOnClose`）；AI 未接入，暂只回显用户消息 |
| `config.yaml` | 窗口尺寸、启动位置、各状态 GIF 路径、走动速度/时长、待机随机时长、三项行为决策概率、click/lost/random 截断上限、lost 触发概率 |

## 已实现的功能

- [x] 项目目录结构与配置文件骨架
- [x] 无边框、透明背景、始终置顶、不在任务栏显示的窗口
- [x] idle GIF 循环播放（stand.gif）
- [x] 启动落位：默认右下角，可配置居中
- [x] 左键按住拖拽换位（拖动中播放 drag.gif，按下点跟手不跳变）
- [x] 配置文件驱动窗口尺寸与动画路径（相对路径自动解析）
- [x] 依赖环境：Python 3.13 + PySide6 6.12 + PyYAML 6.0 + openai 3.3
- [x] 走动状态机：随机 360° 方向走动（可斜向/上下），小数累加防取整卡住
- [x] 碰屏幕四边按对应轴反转速度分量并钳制位置（碰左右翻 vx、碰上下翻 vy）
- [x] 走动 GIF 按水平分量选择：`vx < 0` 播 `walk-left.gif`，否则 `walk-right.gif`，反向瞬间自动切换
- [x] 自主行为循环（待机→决策→执行→回待机）：待机随机时长（`idle_duration_min`~`idle_duration_max`，可配）到点后，在「走动 / 随机动画 / 继续待机」三项间按 `walk_chance`/`random_chance`/`continue_idle_chance` 加权随机决策（三项按和归一化，和为 1 时即精确概率；全 0 则一直待机）；动作播完回待机重新随机计时
- [x] 随机动作（random 状态）：决策选中时从 `animation.random_actions` 列表挑一个 GIF，原地从首帧完整播一遍（不位移）后回待机（与 click/lost 同用 frameChanged 末帧检测；`random_max_ms: 0` 不截断，可配正值兜底）；无素材时退回继续待机
- [x] 左键单击完整播放 click.gif 一次后回待机（末帧检测结束；`click_max_ms: 0` 不截断，可配正值截断）
- [x] 用户操作打断：点击/拖动打断当前动作（走动 / 随机动画 / 待机计时），播对应动画，操作结束后回待机重新计时
- [x] `set_walk_enabled()` 开关走动（已由右键菜单「暂停/恢复走动」调用）
- [x] 走丢效果：每次走动结束后按概率（`lost_chance`，默认 0.3）播放 `walk/get lost.gif` 一次后回待机；支持 `lost_max_ms` 截断上限
- [x] 移除待机随机混播（原 `idle_random_chance`）：待机固定播 `stand.gif`，`random/` 目录 GIF（`animation.random_actions` 列表）只作为决策后的「随机动作」出现，职责单一
- [x] 修复 `config.py` 对空动画路径（`talk:`/`error:` 留空为 None）的崩溃
- [x] 修复素材目录重组导致的启动空白：`stand.gif` 迁至 `assets/idle/`，`config.yaml` 路径同步更新；`talk`/`error` 改为留空
- [x] 右键菜单（最小版，原生 `QMenu`）：开始对话（占位，`_on_chat_requested` 空实现）/ 暂停走动↔恢复走动（按 `walk_enabled` 动态文案，调 `set_walk_enabled`）/ 回到屏幕中央（`_place("center")`）/ 打开配置文件（`os.startfile(CONFIG_PATH)`）/ 退出（`QApplication.quit`）；菜单与「动作→回调」映射由 `_build_context_menu()` 统一构建，`contextMenuEvent` exec 后查映射分发，未选中（None）不动作
- [x] 右键即回待机：`contextMenuEvent` 一进来就 `_enter_idle()`（打断走动/随机动画/点击并播 stand.gif），再停掉待机计时使菜单期间保持静止，菜单关闭后恢复自主行为计时
- [x] 随机动画素材扩充：`animation.random_actions` 增至 6 项（新增 dance / look around / groom myself / wind flow）；行为参数调优：待机 10~40s→5~20s、`walk_chance` 0.5→0.6、`continue_idle_chance` 0.2→0.1、单次走动 3~8s→4~8s
- [x] 对话框（AI 未接入的最小版，`src/chat_dialog.py`）：右键菜单「开始对话」唤起，桌宠正上方落位（放不下落下方、按外框钳制屏内）；只读日志 + 输入框 + 发送（Enter/按钮均可）多轮输入骨架，`_history` 仅存本次会话；关闭方式 X / Esc / 点外部（窗口失活即关），`closeEvent` 清空记忆并 emit `closed`，`WA_DeleteOnClose` 销毁实例（下次打开为全新对象）；重复唤起只 raise 已开窗口
- [x] 对话期间原地待机：开框时 `_enter_idle()` 回播 stand.gif 并停待机计时，`chat_open` 拦住 `_schedule_next_behavior`/`_decide_action`（期间左键点完 click 也不恢复计时）；关框后 `_on_chat_closed` 恢复自主行为计时

## 已知问题 / TODO

- [ ] `talk`、`error` GIF 未制作，配置暂留空，待素材就绪后填路径并接入状态机
- [ ] 气泡（QPainter 自绘圆角矩形+尾巴、自动换行、流式刷新）未实现
- [ ] 对话框待 AI 接入后补齐：流式输出呈现、输出中禁用用户输入、输出中关闭即中断请求（多轮输入骨架、关闭清空、关闭恢复走动已实现）
- [ ] AI 接入（OpenAI SDK、base_url 切换、流式、失败播 error）未实现
- [ ] 气泡样式配置项缺失：圆角、边框色、填充色、透明度、字体、字号、最大宽度
- [ ] `system_prompt.txt` 人格配置文件未创建

## 版本控制（Git）

- 2026-10-12：`git init`（main 分支）初始化本仓库，新增 `.gitignore`（排除 `__pycache__/`、`*.pyc`、`_test_log.txt`、`venv/`、`.pytest_cache/`、`.ruff_cache/`）
- 2026-10-12：首次提交 `feat: 桌宠项目初始版本`，内容为代码 + 配置 + handbook + progress.md + 8 个 GIF 素材（约 11MB，纳入版本控制）
- 2026-10-12：打标签 `v1.0.0` 标记当前稳定版本
- 2026-10-12：添加远端 `origin` → `https://github.com/Iloveazusa008/my-tiny-desktop-pet.git`，`git push -u origin main --tags` 推送至 GitHub（账号 `Iloveazusa008`）
- 2026-10-12：提交 `2d214c2 docs(progress): 记录 git 初始化与 sslverify=false 踩坑原因` 并推送
- 2026-10-12：提交 `600e6da feat: 重构自主行为循环，新增随机动作状态`（4 文件，+121/−69），打标签 `v2.0.0`（备注：修改了动作循环逻辑），推送 `main` 与标签至 GitHub
- 2026-10-12：提交 `feat: 添加右键菜单与对话框`（新增 `src/chat_dialog.py`、4 个 random GIF、右键菜单与对话期间挂起自主行为、参数调优），打标签 `v2.1.0`（备注：添加右键菜单和对话框），推送 `main` 与标签至 GitHub

日常提交流程：`git add .` → `git commit -m "描述"` → `git push`；确认某个版本不错时可用 `git tag v1.x.x` 再 `git push --tags`。

## 备注 / 踩坑记录

- PySide6 6.12 的 `QMovie` 没有 `setLoopCount`：单次/完整播完靠 `frameChanged` 检测末帧（`_on_one_shot_frame`）+ 可选 `*_max_ms` 定时截断双保险；click/lost/random 共用此机制（见 `ONE_LOOP_STATES`）
- 随机动画「完整播一遍」= 从首帧播到末帧即结束。当前 `assets/random/` 素材约 101 帧、单遍约 10 秒，嫌长可配 `random_max_ms` 截断
- 待机动画现在固定用 `idle` 键（stand.gif），`random_action_*` 动画只在 RANDOM 状态播放，二者不共用；进入 RANDOM 时 `_set_state` 统一 `jumpToFrame(0)` 保证每次从头完整播
- 拖动偏移量 `_drag_offset` 必须在 mousePressEvent 里用「按下点全局坐标 − 窗口左上角」算一次，拖动中重算会导致窗口跳到鼠标左上方
- 斜向速度是浮点，直接对位置取整会因分量 <1px 而卡住，需用小数累加器（`_walk_fx/_walk_fy`）
- PySide6 的方法不能像普通 Python 方法那样被类属性覆盖：给 `QMenu.exec = fake` 打桩后实例调用仍走 C++ 原生实现（进嵌套事件循环卡死）；且程序化 `action.trigger()` 不会让 `menu.exec()` 返回该动作（即使随后 `close()`，exec 也返回 None），只有真实鼠标点击才返回被点动作。菜单测试因此拆两层：`_build_context_menu()` 验证菜单项与回调映射，`_exec_menu(menu, pos)` 这层用实例属性替换来喂入「被点中的动作」走完 `contextMenuEvent` 分发，真实路径仍是 `menu.exec(pos)`
- 对话框「点外部即关」要用 `event()` 拦 `QEvent.Type.WindowDeactivate` 调 `self.close()`，不能用 `focusOutEvent`（它只在整个窗口失焦时触发，子控件之间切换焦点不会走这里，且窗口从未激活过时也不触发）
- 顶层窗口 `move()` 定位的是窗口外框（frame），`geometry()` 是客户区：先 `show()` 拿到真实 `frameGeometry()` 再做屏幕钳制，否则客户区会溢出屏幕几像素（离屏 800×800 下实测 geometry 右边界 802）
- git 全局配置 `http.sslverify=false` 是必需的，不能删：Watt Toolkit（Steam++）加速 GitHub 时会把 hosts 里 `github.com` 等域名指向 `127.0.0.1` 并用自带 `SteamTools Certificate` 做中间人代理，而 git 用自己的 CA bundle（不含该证书），开启校验会报 `SSL peer certificate or SSH remote key was not OK`，导致 push/fetch 失败
